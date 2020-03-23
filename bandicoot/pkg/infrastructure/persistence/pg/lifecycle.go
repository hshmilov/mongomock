package pg

import (
	"context"
)

func (p *Repo) GetLastLifecycle(ctx context.Context) (int, error) {
	var l int
	row := p.pool.QueryRow(ctx, "SELECT id FROM lifecycle ORDER BY id DESC LIMIT 1")
	if err := row.Scan(&l); err != nil {
		return 0, err
	}
	return l, nil
}
