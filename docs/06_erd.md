# SmartFuel ERD

This ERD describes the target data model for the SmartFuel greenfield implementation.

The model supports:

- user authentication
- vehicle fuel efficiency
- user-owned card discount policies
- card policy source and image metadata
- gas station and fuel price data
- recommendation quote history

```mermaid
erDiagram
    USER ||--o{ VEHICLE_PROFILE : owns
    USER ||--o{ USER_CARD : registers
    CARD_POLICY ||--o{ USER_CARD : selected_by
    CARD_POLICY ||--o{ CARD_BENEFIT_SOURCE : discovered_from
    GAS_STATION ||--o{ FUEL_PRICE : has
    USER ||--o{ RECOMMENDATION_QUOTE : requests
    RECOMMENDATION_QUOTE ||--o{ RECOMMENDATION_CANDIDATE : contains
    GAS_STATION ||--o{ RECOMMENDATION_CANDIDATE : evaluated_as
    CARD_POLICY ||--o{ RECOMMENDATION_CANDIDATE : applied_to

    USER {
        bigint id PK
        string email UK
        string username
        string password_hash
        datetime created_at
        datetime updated_at
    }

    VEHICLE_PROFILE {
        bigint id PK
        bigint user_id FK
        string fuel_type
        decimal fuel_efficiency_kmpl
        boolean is_default
        datetime created_at
        datetime updated_at
    }

    CARD_POLICY {
        bigint id PK
        string card_name
        string issuer_name
        string discount_type
        decimal discount_value
        string brand_scope
        int min_payment_amount
        int max_discount_amount
        int monthly_discount_limit
        string source_type
        string verification_status
        string card_image_url
        string source_url
        string source_title
        datetime created_at
        datetime updated_at
    }

    CARD_BENEFIT_SOURCE {
        bigint id PK
        bigint card_policy_id FK
        string source_type
        string provider
        string source_url
        string source_title
        string source_summary
        string image_url
        datetime collected_at
    }

    USER_CARD {
        bigint id PK
        bigint user_id FK
        bigint card_policy_id FK
        int monthly_remaining_discount
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    GAS_STATION {
        bigint id PK
        string external_station_id UK
        string name
        string brand
        string address
        decimal latitude
        decimal longitude
        boolean is_self
        datetime created_at
        datetime updated_at
    }

    FUEL_PRICE {
        bigint id PK
        bigint station_id FK
        string fuel_type
        int price_per_liter
        string source
        datetime collected_at
        datetime created_at
    }

    RECOMMENDATION_QUOTE {
        bigint id PK
        bigint user_id FK
        decimal request_latitude
        decimal request_longitude
        string fuel_type
        decimal target_liters
        decimal fuel_efficiency_kmpl
        decimal radius_km
        string travel_mode
        string distance_source
        string algorithm_version
        datetime created_at
    }

    RECOMMENDATION_CANDIDATE {
        bigint id PK
        bigint quote_id FK
        bigint station_id FK
        bigint selected_card_policy_id FK
        decimal distance_km
        int fuel_price_per_liter
        int refuel_cost
        int card_discount_amount
        int travel_cost
        int effective_total_cost
        int estimated_saving
        int rank_order
        string reason
    }
```

## Domain Notes

`USER` belongs to the `accounts` domain.

`VEHICLE_PROFILE` belongs to the `vehicles` domain.

`CARD_POLICY`, `USER_CARD`, and `CARD_BENEFIT_SOURCE` belong to the `cards` domain.

Card policies can be manually entered or discovered through Naver-based search. Naver-discovered policies remain suggestions until the user confirms or an admin verifies them.

`GAS_STATION`, `FUEL_PRICE`, `RECOMMENDATION_QUOTE`, and `RECOMMENDATION_CANDIDATE` belong to the `stations` domain.

For the first backend slice, only `GAS_STATION` and `FUEL_PRICE` are required.

Recommendation history tables can be implemented after the stateless recommendation API is stable.

For Slice 4, the minimum required card models are `CARD_POLICY` and `USER_CARD`. `CARD_BENEFIT_SOURCE` can be added when implementing Naver discovery.
