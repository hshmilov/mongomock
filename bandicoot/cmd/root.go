package cmd

import (
	"bandicoot/internal"
	"github.com/mitchellh/go-homedir"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"net"
)

// variables used in the flags
var (
	cfgFile string

	pgHostName   string
	pgPort       int
	mgHostname   string
	mgPort       int
	partitionCut int

	// Transfer flags
	transferAdapters     bool
	transferDevices      bool
	transferTags         bool
	transferUsers        bool
	transferOS           bool
	transferRateLimit    int
	transferChunkLimit   int64
	transferDeviceOffset int
	transferFetchCycle   int

	rootCmd = &cobra.Command{
		Use:   "bandicoot",
		Short: "Bandicoot GraphQL Server API",
		Long:  "Bandicoot GraphQL Server API",
	}
)

func Execute() error {
	return rootCmd.Execute()
}

func init() {

	cobra.OnInitialize(initConfig, initLog)

	// Add Base commands
	rootCmd.AddCommand(transferCmd)
	rootCmd.AddCommand(apiCMD)
	// Add common flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.bandicoot.yaml)")
	rootCmd.PersistentFlags().StringVar(&pgHostName, "pgHostname", "127.0.0.1", "Postgres hostname")
	rootCmd.PersistentFlags().IntVar(&pgPort, "pgPort", 5432, "Postgres hostname")
	rootCmd.PersistentFlags().StringVar(&mgHostname, "mgHostname", "127.0.0.1", "Mongo hostname")
	rootCmd.PersistentFlags().IntVar(&mgPort, "mgPort", 27017, "Mongo hostname")
	rootCmd.PersistentFlags().IntVar(&partitionCut, "partitionCut", 3, "How many partitions to keep before removing them")

	// Logging configuration flags
	rootCmd.PersistentFlags().Bool("enableConsoleLog", false, "log should be written to console (stdout)")
	rootCmd.PersistentFlags().Bool("enableFileLogging", true, "enableFileLogging makes the framework log to a file")
	rootCmd.PersistentFlags().Bool("verbose", false, "Enable debug logging")
	rootCmd.PersistentFlags().Bool("enableTraceLogging", false, "Enable trace logging")
	rootCmd.PersistentFlags().String("logDirectory", "./", "directory to write log file")
	rootCmd.PersistentFlags().String("logFilename", "bandicoot.axonius.log", "name of log file")
	rootCmd.PersistentFlags().Int("maxSize", 30, "MaxSize the max size in MB of the logfile before it's rolled")
	rootCmd.PersistentFlags().Int("maxBackups", 5, "MaxBackups the max number of rolled files to keep")
	rootCmd.PersistentFlags().Int("maxAge", 0, "MaxAge the max age in days to keep a logfile")

	// Transfer cmd flags
	transferCmd.Flags().BoolVar(&transferAdapters, "transferAdapters", true, "Transfer adapter data")
	transferCmd.Flags().BoolVar(&transferDevices, "transferDevices", true, "Transfer device data")
	transferCmd.Flags().BoolVar(&transferTags, "transferTags", true, "Transfer tags data")
	transferCmd.Flags().BoolVar(&transferUsers, "transferUsers", true, "Transfer users data")
	transferCmd.Flags().BoolVar(&transferOS, "transferOS", true, "Transfer operating systems data")
	transferCmd.Flags().IntVar(&transferRateLimit, "transferRateLimit", 10, "Transfer rate limit (sleeps in seconds) between transfers")
	transferCmd.Flags().Int64Var(&transferChunkLimit, "transferChunkLimit", 1000, "Chunk transfer limit")
	transferCmd.Flags().IntVar(&transferDeviceOffset, "transferDeviceOffset", 0, "Transfer device offset")
	transferCmd.Flags().IntVar(&transferFetchCycle, "transferFetchCycle", 0, "Transfer fetch cycle")

	// API cmd flags
	apiCMD.Flags().Int("apiPort", 9090, "Port API will listen for incoming connections")
	apiCMD.Flags().Bool("apiDebug", false, "Whether to run API in debug mode, by default it's true")
	apiCMD.Flags().IP("apiAddr", net.ParseIP("127.0.0.1"), "IP address server will listen on")
	apiCMD.Flags().Bool("apiDisableAuth", false, "Disable need for authentication in APIs")
	apiCMD.Flags().String("apiSSLCert", "", "Path to SSL certificate, if path is empty service will run in HTTP")
	apiCMD.Flags().String("apiSSLKey", "", "Path to SSL key, if path is empty service will run in HTTP")

	// Viper configuration flags
	for _, f := range []string{"pgHostname", "pgPort", "mgHostname", "mgPort", "partitionCut",
		"enableConsoleLog", "enableFileLogging", "verbose", "enableTraceLogging",
		"logDirectory", "logFilename", "maxSize", "maxBackups", "maxAge"} {
		_ = viper.BindPFlag(f, rootCmd.PersistentFlags().Lookup(f))
	}
	for _, f := range []string{"apiPort", "apiDebug", "apiAddr", "apiDisableAuth", "apiSSLCert", "apiSSLKey"} {
		_ = viper.BindPFlag(f, apiCMD.Flags().Lookup(f))
	}
}

func initLog() {
	// update global logger
	log.Logger = *internal.Configure(internal.Config{
		ConsoleLoggingEnabled: viper.GetBool("enableConsoleLog"),
		Debug:                 viper.GetBool("verbose"),
		Trace:                 viper.GetBool("enableTraceLogging"),
		FileLoggingEnabled:    viper.GetBool("enableFileLogging"),
		Directory:             viper.GetString("logDirectory"),
		Filename:              viper.GetString("logFilename"),
		MaxSize:               viper.GetInt("maxSize"),
		MaxBackups:            viper.GetInt("maxBackups"),
		MaxAge:                viper.GetInt("maxAge"),
	})
}

func initConfig() {
	viper.SetEnvPrefix("bandicoot")
	if cfgFile != "" {
		// Use config file from the flag.
		viper.SetConfigFile(cfgFile)
	} else {
		// Find home directory.
		home, err := homedir.Dir()
		if err != nil {
			log.Fatal().Err(err)
		}
		// Set configuration type to be yaml
		viper.SetConfigType("yaml")
		// Search config in home directory with name "config" (without extension).
		viper.AddConfigPath(home)
		viper.AddConfigPath("/etc/bandicoot/")
		viper.SetConfigName("config")
	}

	// Automatically load flags from environment
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		log.Info().Str("file", viper.ConfigFileUsed()).Msg("Loaded configuration file")
	}
}
