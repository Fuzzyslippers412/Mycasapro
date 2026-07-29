package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/config"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/database"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/filestore"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/httpapi"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/notification"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

func main() {
	cfg := config.Load()
	if err := cfg.Validate(); err != nil {
		log.Fatal(err)
	}
	ctx := context.Background()

	appStore, cleanup, err := buildStore(ctx, cfg)
	if err != nil {
		log.Fatal(err)
	}
	if cleanup != nil {
		defer cleanup()
	}

	fileStore, err := filestore.NewLocalStore(cfg.UploadDir)
	if err != nil {
		log.Fatal(err)
	}
	server := httpapi.NewServerWithFileStore(cfg, appStore, fileStore)
	workerCtx, stopWorker := context.WithCancel(context.Background())
	defer stopWorker()
	if cfg.EmailDeliveryEnabled() {
		go notification.NewWorker(appStore, notification.NewSMTPSender(cfg)).Run(workerCtx)
	}

	log.Printf("mycasapro app listening on %s (%s, store=%s)", cfg.Addr, cfg.Env, cfg.StoreBackend)

	go func() {
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatal(err)
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh
	stopWorker()

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Fatal(err)
	}
}

func buildStore(ctx context.Context, cfg config.Config) (store.Store, func() error, error) {
	switch cfg.StoreBackend {
	case "memory":
		if cfg.Env == "production" {
			return nil, nil, errors.New("memory store is disabled in production; configure APP_DATABASE_URL")
		}
		return store.NewMemoryStore(), nil, nil
	case "postgres":
		db, err := database.OpenPostgres(ctx, cfg.DatabaseURL)
		if err != nil {
			return nil, nil, err
		}
		if cfg.AutoMigrate {
			if err := database.RunMigrations(ctx, db, cfg.MigrationsDir); err != nil {
				_ = db.Close()
				return nil, nil, err
			}
		}
		return store.NewPostgresStore(db), db.Close, nil
	default:
		return nil, nil, errUnknownStoreBackend(cfg.StoreBackend)
	}
}

type unknownStoreBackendError string

func (e unknownStoreBackendError) Error() string {
	return "unknown store backend: " + string(e)
}

func errUnknownStoreBackend(value string) error {
	return unknownStoreBackendError(value)
}
