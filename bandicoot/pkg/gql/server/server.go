package server

import (
	"bandicoot/pkg/gql"
	"context"
	"fmt"
	"github.com/gin-contrib/cors"
	"github.com/gin-contrib/logger"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"github.com/spf13/viper"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func GinContextToContextMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		ctx := context.WithValue(c.Request.Context(), "GinContextKey", c)
		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

func Serve() {
	if err := gql.InitializeDatabase(); err != nil {
		return
	}
	gin.SetMode(gin.ReleaseMode)
	// if api debug flag is set as True set gin to debug mode
	if viper.GetBool("apiDebug") {
		gin.SetMode(gin.DebugMode)
	}

	//authMiddleware, err := InitAuthMiddleware()
	//if err != nil {
	//	log.Err(err).Msg("Failed to create jwt")
	//	return
	//}
	// Setting up Gin
	r := gin.New()
	// add cors to everyone
	r.Use(cors.Default())
	// Add Panic Recovery
	r.Use(gin.Recovery())
	// Add a logger middleware, which:
	//   - Logs all requests, like a combined access and error log.
	//   - Logs to stdout.
	r.Use(logger.SetLogger())
	// Allow access to the gin context from graphql resolvers
	r.Use(GinContextToContextMiddleware())

	// TODO: future support for auth
	//r.POST("/login", authMiddleware.LoginHandler)
	//r.NoRoute(authMiddleware.MiddlewareFunc(), func(c *gin.Context) {
	//	claims := jwt.ExtractClaims(c)
	//	log.Printf("NoRoute claims: %#v\n", claims)
	//	c.JSON(404, gin.H{"code": "PAGE_NOT_FOUND", "message": "Page not found"})
	//})
	//auth := r.Group("/auth")
	//// Refresh time can be longer than token timeout
	//auth.GET("/refresh_token", authMiddleware.RefreshHandler)
	//auth.Use(authMiddleware.MiddlewareFunc()){}

	// Always open for now
	r.POST("/query", graphqlHandler())
	r.GET("/", playgroundHandler())
	r.POST("/transfer", transferHandler)

	apiPort := viper.GetInt("apiPort")
	apiAddr := viper.GetString("apiAddr")
	srv := &http.Server{
		Addr:    fmt.Sprintf("%s:%d", apiAddr, apiPort),
		Handler: r,
	}

	log.Info().Str("address", fmt.Sprintf("%s:%d", apiAddr, apiPort)).Msg("Starting server")
	go func() {
		sslKey, sslCert := viper.GetString("apiSSLKey"), viper.GetString("apiSSLCert")
		if sslCert != "" && sslKey != "" {
			log.Info().Str("key", sslKey).Str("cert", sslCert).Msg("Running in SSL mode")
			if err := srv.ListenAndServeTLS(sslCert, sslKey); err != nil && err != http.ErrServerClosed {
				log.Fatal().Err(err).Msg("Failed to listen")
			}
		} else if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("Failed to listen")
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server with
	// a timeout of 5 seconds.
	quit := make(chan os.Signal, 1)
	// kill (no param) default send syscall.SIGTERM
	// kill -2 is syscall.SIGINT
	// kill -9 is syscall.SIGKILL but can't be catch, so don't need add it
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	for {
		select {
		case <-quit:
			func() {
				ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
				defer cancel()
				if err := srv.Shutdown(ctx); err != nil {
					log.Fatal().Err(err).Msg("Server shutdown...")
				}
			}()
			return
		}
	}
}
