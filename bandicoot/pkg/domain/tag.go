package domain

import (
	"context"
)

// TagLevel - level of important of the tag
type TagLevel string

const (
	NONE     TagLevel = "None"
	INFO     TagLevel = "Info"
	WARNING  TagLevel = "Warning"
	CRITICAL TagLevel = "Critical"
)

// TagCreator - who created the Tag
type TagCreator string

const (
	UNKNOWN TagCreator = "Unknown"
	USER    TagCreator = "User"
	AXONIUS TagCreator = "System"
)

type Tag struct {
	Name string
	// The level of the Tag
	Level TagLevel
	// Who created the tag
	Creator TagCreator
}

// Describes the interface for interacting with tags
type TagsRepository interface {
	// Find correlated devices
	FindTags(ctx context.Context, skip, limit int) ([]Tag, error)
	// Creates a new Tag
	CreateTag(ctx context.Context, t Tag) error
}
