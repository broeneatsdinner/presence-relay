# Chicago Reference Scenario

This public-safe fixture replaces invented geography with a real, distant city
scenario that has realistic corridor shape and public contextual data.

The fixture uses public Chicago North Side landmarks:

| Role | Slug | Public name | Address |
| --- | --- | --- | --- |
| Route endpoint | `sheridan-plaza` | Sheridan Plaza | 4607 N Sheridan Rd, Chicago, IL 60640 |
| Context landmark | `loyola-lake-shore-campus` | Loyola University Chicago Lake Shore Campus | 6511 N Sheridan Rd, Chicago, IL 60660 |
| Context landmark | `gentile-arena` | Joseph J. Gentile Arena | 6526 N Winthrop Ave, Chicago, IL 60660 |
| Route endpoint | `kilmer-elementary` | Joyce Kilmer Elementary School | 6700 N Greenview Ave, Chicago, IL 60626 |

The reference route is:

```text
public multifamily residential property
  -> urban corridor
    -> university campus and athletic venue context
      -> short continuation beyond campus
        -> public elementary-school destination
```

The apartment, university venue, and school arrangement is useful because it
supports realistic examples for corridor geometry, venue proximity, public
scheduled events, daylight, weather, and school-calendar context. The
university and arena can affect route conditions without being route endpoints.

This fixture does not assert that anyone in the project lives at Sheridan
Plaza, attends Kilmer Elementary, travels this route, or has any relationship
to the listed locations. It is geographically unrelated to the live deployment.

Example route sessions, timestamps, conditions, venue events, baselines, and
inference results remain synthetic. Raw private route history, private
coordinates, family schedules, phone telemetry, screenshots, and live
infrastructure details must not be copied into this fixture.

## Coordinate And Geometry Sources

Point coordinates use OpenStreetMap Nominatim results retrieved on
2026-06-15. Coordinates in GeoJSON examples are ordered as
`[longitude, latitude]`.

Route corridor geometry uses the public OSRM demo service, retrieved on
2026-06-15, with the public fixture points as route waypoints. The example
geometry is for contract testing and documentation only; it is not a production
routing source. OSRM demo durations are routing-reference estimates without
live traffic; they are not observed trip durations.

The primary route, `sheridan-corridor`, is constrained through the Loyola and
Gentile area. OSRM step names for that route include North Sheridan Road, West
Loyola Avenue, North Winthrop Avenue, West Albion Avenue, West Pratt Boulevard,
and North Bosworth Avenue.

The alternate route, `ashland-clark-alternate`, comes from OSRM alternate
routing between the same endpoint fixtures. OSRM step names include North
Sheridan Road, West Wilson Avenue, North Broadway, West Lawrence Avenue, North
Ashland Avenue, North Clark Street, West Pratt Boulevard, and North Bosworth
Avenue.

The route-session duration examples are synthetic observed examples. Baseline
and inference durations are synthetic analytical examples. None of the
durations assert an actual trip by any person.
