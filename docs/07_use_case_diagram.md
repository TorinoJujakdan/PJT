# SmartFuel Use Case Diagram

This diagram shows how users, external data providers, and operators interact with SmartFuel.

```mermaid
flowchart LR
    guest["Guest User"]
    member["Logged-in User"]
    admin["Admin / Operator"]
    opinet["Opinet API"]
    naver["Naver Search API"]
    nav["Navigation API"]

    subgraph smartfuel["SmartFuel Service"]
        uc_current_location["Use current location"]
        uc_manual_location["Enter location manually"]
        uc_search_nearby["Search nearby stations"]
        uc_quote["Request recommendation quote"]
        uc_view_reason["View recommendation reason"]
        uc_register["Register account"]
        uc_login["Login"]
        uc_vehicle["Manage vehicle profile"]
        uc_cards["Manage card policies"]
        uc_manual_card["Enter card benefit manually"]
        uc_discover_card["Discover card benefits via Naver"]
        uc_confirm_card["Confirm discovered card benefit"]
        uc_view_card_image["View card image"]
        uc_station_detail["View station detail"]
        uc_sync_price["Sync fuel price data"]
        uc_dummy_data["Load dummy station data"]
        uc_health["Check service health"]
    end

    guest --> uc_current_location
    guest --> uc_manual_location
    guest --> uc_search_nearby
    guest --> uc_quote
    guest --> uc_view_reason
    guest --> uc_register
    guest --> uc_login
    guest --> uc_station_detail

    member --> uc_current_location
    member --> uc_manual_location
    member --> uc_search_nearby
    member --> uc_quote
    member --> uc_view_reason
    member --> uc_vehicle
    member --> uc_cards
    member --> uc_manual_card
    member --> uc_discover_card
    member --> uc_confirm_card
    member --> uc_view_card_image
    member --> uc_station_detail

    admin --> uc_sync_price
    admin --> uc_dummy_data
    admin --> uc_health

    uc_sync_price --> opinet
    uc_discover_card --> naver
    uc_quote -. "future route distance" .-> nav

    uc_quote --> uc_search_nearby
    uc_quote --> uc_view_reason
    uc_cards --> uc_manual_card
    uc_cards --> uc_discover_card
    uc_discover_card --> uc_confirm_card
    uc_confirm_card --> uc_view_card_image
```

## Use Case Summary

| Actor | Main Goal | Use Cases |
|---|---|---|
| Guest User | Get a stateless recommendation | Current location, manual location, nearby station search, recommendation quote |
| Logged-in User | Get a personalized recommendation | Vehicle profile, manual card benefit input, Naver card discovery, card confirmation, recommendation quote |
| Admin / Operator | Keep service data and runtime healthy | Fuel price sync, dummy data load, health check |
| Opinet API | Provide fuel price data | Fuel price synchronization |
| Naver Search API | Provide card benefit discovery metadata | Card benefit candidate search |
| Navigation API | Provide route distance later | Future route-based distance calculation |

## Product Flow

```text
User location
-> nearby station candidate search
-> fuel price comparison
-> vehicle travel cost calculation
-> confirmed card discount calculation
-> effective total cost ranking
-> recommendation reason and card image display
```
