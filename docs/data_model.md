# 🗄️ Data Storage

### `Dealer`

| Field | Type |
|-------|------|
| `google_place_id` | str (unique) |
| `name`, `address`, `city` | str |
| `lat`, `lng` | float |
| `rating` | float \| null |
| `user_ratings_total` | int |
| `website`, `phone` | str \| null |
| `last_synced_at` | datetime (auto_now) |

### `SearchCache`

| Field | Type |
|-------|------|
| `query_key` | str (unique) |
| `results_json` | json |
| `created_at` | datetime |

### `User`

| Field | Type |
|-------|------|
| `email` | str (unique, USERNAME_FIELD) |
| `google_sub` | str \| null (unique) |
| `plan` | str (`free` / `premium`) |
| `daily_quota` | int (default 15) |
| `ai_daily_quota` | int (default 15) |
| `terms_accepted` | bool |

> ℹ️ Usage counters (`used_today`) are stored in Redis: `quota:user:{pk}:{date}` and `quota:anon:{ip}:{date}`, TTL until next midnight.

### `Favorite`

| Field | Type |
|-------|------|
| `user` | FK→User |
| `place_id` | str |
| `name`, `address`, `city` | str |
| `rating` | float \| null |
| `phone`, `website` | str |
| `lat`, `lng` | float \| null |
| `created_at` | datetime |

unique_together: `(user, place_id)`

### `PopularSearch`

| Field | Type |
|-------|------|
| `city` | str (unique) |
| `count` | int |
| `updated_at` | datetime (auto_now) |

### `UserSearchHistory`

| Field | Type |
|-------|------|
| `user` | FK→User |
| `city` | str |
| `searched_at` | datetime |