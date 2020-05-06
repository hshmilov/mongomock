package internal

import (
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"gopkg.in/natefinch/lumberjack.v2"
	"io"
	"os"
	"path"
)

type FilteredWriter struct {
	w zerolog.LevelWriter
	level zerolog.Level
}
func (w *FilteredWriter) Write(p []byte) (n int, err error) {
	return w.w.Write(p)
}
func (w *FilteredWriter) WriteLevel(level zerolog.Level, p []byte) (n int, err error) {
	if level >= w.level {
		return w.w.WriteLevel(level, p)
	}
	return len(p), nil
}

// Configuration for logging
type Config struct {
	// Enable console logging
	ConsoleLoggingEnabled bool
	// Enable debug logging
	Debug bool
	// Enable trace level logging
	Trace bool
	// FileLoggingEnabled makes the framework log to a file
	// the fields below can be skipped if this value is false!
	FileLoggingEnabled bool
	// Directory to log to to when file logging is enabled
	Directory string
	// Filename is the name of the logfile which will be placed inside the directory
	Filename string
	// MaxSize the max size in MB of the logfile before it's rolled
	MaxSize int
	// MaxBackups the max number of rolled files to keep
	MaxBackups int
	// MaxAge the max age in days to keep a logfile
	MaxAge int
}

type Logger struct {
	*zerolog.Logger
}

// Configure sets up the logging framework
//
// In production, the container logs will be collected and file logging should be disabled. However,
// during development it's nicer to see logs as text and optionally write to a file when debugging
// problems in the containerized pipeline
//
// The output log file will be located at /var/log/service-xyz/service-xyz.log and
// will be rolled according to configuration set.
func Configure(config Config) *zerolog.Logger {
	var writers []io.Writer

	if config.ConsoleLoggingEnabled {
		writers = append(writers, zerolog.ConsoleWriter{Out: os.Stderr})
	}

	if config.FileLoggingEnabled {
		// Create a logging file that defaults that always info level
		writers = append(writers, &FilteredWriter{
			zerolog.MultiLevelWriter(newRollingFile(config, false)),
			zerolog.InfoLevel},
		)
	}

	zerolog.SetGlobalLevel(zerolog.InfoLevel)
	if config.Debug {
		// Add a .debug log file if we are allowing file logging
		if config.FileLoggingEnabled {
			writers = append(writers, &FilteredWriter{
				zerolog.MultiLevelWriter(newRollingFile(config, true)),
				zerolog.DebugLevel},
			)
		}
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	}
	if config.Trace {
		zerolog.SetGlobalLevel(zerolog.TraceLevel)
	}

	zerolog.TimestampFieldName = "@timestamp"
	mw := zerolog.MultiLevelWriter(writers...)
	logger := zerolog.New(mw).With().Timestamp().Logger()

	logger.Info().
		Bool("fileLogging", config.FileLoggingEnabled).
		Bool("consoleLogging", config.ConsoleLoggingEnabled).
		Str("logDirectory", config.Directory).
		Str("fileName", config.Filename).
		Bool("debug", config.Debug).
		Bool("trace", config.Trace).
		Int("maxSizeMB", config.MaxSize).
		Int("maxBackups", config.MaxBackups).
		Int("maxAgeInDays", config.MaxAge).
		Msg("logging configured")

	return &logger
}

func newRollingFile(config Config, debug bool) io.Writer {
	if err := os.MkdirAll(config.Directory, 0744); err != nil {
		log.Error().Err(err).Str("path", config.Directory).Msg("can't create log directory")
		return nil
	}
	fileName := config.Filename
	if debug {
		fileName += ".debug"
	}
	return &lumberjack.Logger{
		Filename:   path.Join(config.Directory, fileName),
		MaxBackups: config.MaxBackups, // files
		MaxSize:    config.MaxSize,    // megabytes
		MaxAge:     config.MaxAge,     // days
	}
}
