package cmd

import (
	"bandicoot/pkg/gql/server"
	"github.com/spf13/cobra"
)

var apiCMD = &cobra.Command{
	Use:   "api",
	Short: "Serves api in rest API",
	Run:   serveAPI,
}

func serveAPI(_ *cobra.Command, _ []string) {
	server.Serve()
}
