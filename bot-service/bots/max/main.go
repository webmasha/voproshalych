package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	maxbot "github.com/max-messenger/max-bot-api-client-go"
	"github.com/max-messenger/max-bot-api-client-go/schemes"
)

// Settings хранит настройки запуска MAX-адаптера.
type Settings struct {
	MaxBotToken               string
	BotCoreURL                string
	BotCoreTimeoutSeconds     time.Duration
	RequestDelayAfterFailures time.Duration
}

// IncomingMessage описывает JSON-контракт входящего сообщения для core.
type IncomingMessage struct {
	Platform  string         `json:"platform"`
	UserID    string         `json:"user_id"`
	ChatID    string         `json:"chat_id"`
	Text      string         `json:"text"`
	MessageID string         `json:"message_id,omitempty"`
	Timestamp string         `json:"timestamp,omitempty"`
	Metadata  map[string]any `json:"metadata"`
}

// OutgoingAction описывает действие, которое должен выполнить адаптер.
type OutgoingAction struct {
	Type     string         `json:"type"`
	Text     string         `json:"text,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// BotResponse описывает ответ core-сервиса.
type BotResponse struct {
	Actions []OutgoingAction `json:"actions"`
}

// CoreClient отправляет нормализованные сообщения в общий core.
type CoreClient struct {
	baseURL string
	client  *http.Client
}

// NewSettings считывает настройки из переменных окружения.
func NewSettings() Settings {
	timeoutSeconds := 10 * time.Second
	if rawTimeout := os.Getenv("BOT_CORE_TIMEOUT_SECONDS"); rawTimeout != "" {
		if parsedTimeout, err := time.ParseDuration(rawTimeout + "s"); err == nil {
			timeoutSeconds = parsedTimeout
		}
	}

	return Settings{
		MaxBotToken:               os.Getenv("MAX_BOT_TOKEN"),
		BotCoreURL:                valueOrDefault(os.Getenv("BOT_CORE_URL"), "http://127.0.0.1:8000"),
		BotCoreTimeoutSeconds:     timeoutSeconds,
		RequestDelayAfterFailures: 2 * time.Second,
	}
}

// NewCoreClient создает HTTP-клиент для вызовов core-сервиса.
func NewCoreClient(settings Settings) *CoreClient {
	return &CoreClient{
		baseURL: settings.BotCoreURL,
		client: &http.Client{
			Timeout: settings.BotCoreTimeoutSeconds,
		},
	}
}

// ProcessMessage отправляет сообщение в core и возвращает список действий.
func (c *CoreClient) ProcessMessage(ctx context.Context, payload IncomingMessage) (BotResponse, error) {
	body, err := json.Marshal(payload)
	if err != nil {
		return BotResponse{}, fmt.Errorf("не удалось сериализовать запрос в core: %w", err)
	}

	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/messages",
		bytes.NewReader(body),
	)
	if err != nil {
		return BotResponse{}, fmt.Errorf("не удалось создать запрос в core: %w", err)
	}

	request.Header.Set("Content-Type", "application/json")

	response, err := c.client.Do(request)
	if err != nil {
		return BotResponse{}, fmt.Errorf("не удалось отправить запрос в core: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode >= http.StatusBadRequest {
		responseBody, _ := io.ReadAll(response.Body)
		return BotResponse{}, fmt.Errorf(
			"core вернул статус %d: %s",
			response.StatusCode,
			string(responseBody),
		)
	}

	var botResponse BotResponse
	if err := json.NewDecoder(response.Body).Decode(&botResponse); err != nil {
		return BotResponse{}, fmt.Errorf("не удалось разобрать ответ core: %w", err)
	}

	return botResponse, nil
}

func main() {
	settings := NewSettings()
	if settings.MaxBotToken == "" {
		log.Fatal("MAX_BOT_TOKEN is not set")
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, os.Interrupt)
	defer stop()

	api, err := maxbot.New(settings.MaxBotToken)
	if err != nil {
		log.Fatalf("не удалось создать MAX API клиент: %v", err)
	}

	coreClient := NewCoreClient(settings)

	for update := range api.GetUpdates(ctx) {
		if err := handleUpdate(ctx, api, coreClient, update); err != nil {
			log.Printf("ошибка обработки MAX update: %v", err)
			time.Sleep(settings.RequestDelayAfterFailures)
		}
	}
}

// handleUpdate обрабатывает только текстовые сообщения и пересылает их в core.
func handleUpdate(
	ctx context.Context,
	api *maxbot.Api,
	coreClient *CoreClient,
	update any,
) error {
	messageUpdate, ok := update.(*schemes.MessageCreatedUpdate)
	if !ok {
		return nil
	}

	text := messageUpdate.Message.Body.Text
	if text == "" {
		return nil
	}

	payload, err := buildIncomingMessage(messageUpdate)
	if err != nil {
		return err
	}

	response, err := coreClient.ProcessMessage(ctx, payload)
	if err != nil {
		if sendErr := sendFallbackMessage(ctx, api, messageUpdate); sendErr != nil {
			return errors.Join(err, sendErr)
		}
		return err
	}

	for _, action := range response.Actions {
		if action.Type != "send_text" || action.Text == "" {
			continue
		}

		message := maxbot.NewMessage()
		message.SetText(action.Text)

		switch {
		case messageUpdate.Message.Recipient.ChatId != 0:
			message.SetChat(messageUpdate.Message.Recipient.ChatId)
		case messageUpdate.Message.Sender.UserId != 0:
			message.SetUser(messageUpdate.Message.Sender.UserId)
		default:
			return fmt.Errorf("в MAX update нет chat_id и user_id для ответа")
		}

		if err := api.Messages.Send(ctx, message); err != nil {
			return fmt.Errorf("не удалось отправить ответ в MAX: %w", err)
		}
	}

	return nil
}

// buildIncomingMessage нормализует MAX update к контракту core.
func buildIncomingMessage(update *schemes.MessageCreatedUpdate) (IncomingMessage, error) {
	message := update.Message

	var userID string
	if message.Sender.UserId != 0 {
		userID = fmt.Sprintf("%d", message.Sender.UserId)
	}

	var chatID string
	switch {
	case message.Recipient.ChatId != 0:
		chatID = fmt.Sprintf("%d", message.Recipient.ChatId)
	case message.Recipient.UserId != 0:
		chatID = fmt.Sprintf("%d", message.Recipient.UserId)
	}

	if userID == "" || chatID == "" {
		return IncomingMessage{}, fmt.Errorf("в MAX update не хватает user_id или chat_id")
	}

	incoming := IncomingMessage{
		Platform: "max",
		UserID:   userID,
		ChatID:   chatID,
		Text:     message.Body.Text,
		Metadata: map[string]any{},
	}

	if message.Timestamp != 0 {
		incoming.Timestamp = formatUnixTimestamp(message.Timestamp)
	}

	incoming.MessageID = message.Body.Mid
	incoming.Metadata["sender_name"] = message.Sender.Name

	return incoming, nil
}

// sendFallbackMessage отправляет короткий ответ, если core временно недоступен.
func sendFallbackMessage(
	ctx context.Context,
	api *maxbot.Api,
	update *schemes.MessageCreatedUpdate,
) error {
	message := maxbot.NewMessage().SetText("Сервис временно недоступен.")

	switch {
	case update.Message.Recipient.ChatId != 0:
		message.SetChat(update.Message.Recipient.ChatId)
	case update.Message.Sender.UserId != 0:
		message.SetUser(update.Message.Sender.UserId)
	default:
		return fmt.Errorf("некуда отправить fallback-сообщение MAX")
	}

	if err := api.Messages.Send(ctx, message); err != nil {
		return fmt.Errorf("не удалось отправить fallback-сообщение MAX: %w", err)
	}

	return nil
}

func valueOrDefault(value string, defaultValue string) string {
	if value == "" {
		return defaultValue
	}
	return value
}

// formatUnixTimestamp нормализует timestamp из MAX в RFC3339.
func formatUnixTimestamp(timestamp int64) string {
	switch {
	case timestamp >= 1_000_000_000_000_000:
		return time.UnixMicro(timestamp).UTC().Format(time.RFC3339)
	case timestamp >= 1_000_000_000_000:
		return time.UnixMilli(timestamp).UTC().Format(time.RFC3339)
	default:
		return time.Unix(timestamp, 0).UTC().Format(time.RFC3339)
	}
}
