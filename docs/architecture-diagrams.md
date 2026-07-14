# Architecture Diagrams

A physical boundary crossing begins as a small signal. Presence Relay moves
that signal through deliberately separated trust domains until it becomes
durable local state.

These diagrams describe implemented behavior and the deterministic local demo.
They do not depict roadmap features as operational.

## Production Trust Boundary

The production architecture separates public ingress from trusted-side
processing. The public relay authenticates, validates, and queues accepted
events. The trusted LAN target remains behind the private delivery boundary and
commits the raw event before creating derived projections or enrichment.

```mermaid
flowchart LR
	subgraph mobile["UNTRUSTED / MOBILE"]
		shortcut["iPhone Shortcut"]
		payload["arrive | leave JSON"]
	end

	subgraph relay["PUBLIC RELAY"]
		webhook["webhook receiver<br/>/hook/presence"]
		auth["authenticate request"]
		validate["validate event + place"]
		queue[("durable delivery queue<br/>strict FIFO")]
	end

	subgraph boundary["PRIVATE DELIVERY BOUNDARY"]
		delivery["controlled private-side delivery path"]
	end

	subgraph lan["TRUSTED LAN"]
		accept["presence-relay acceptance"]
		db[("presence.sqlite<br/>raw event record")]
		projections["derived projections<br/>.presence-* files"]
		enrich["asynchronous enrichment<br/>one oldest unfinished event"]
		operator["read-only operator views<br/>Unicode tables / JSON"]
		viewer["local viewer"]
	end

	shortcut -->|"authenticated HTTPS event"| payload
	payload --> webhook
	webhook --> auth
	auth --> validate
	validate --> queue
	queue -->|"oldest unfinished row"| delivery
	delivery --> accept
	accept --> db
	db --> projections
	db --> enrich
	enrich --> db
	operator -->|"reads independent streams"| db
	viewer -->|"reads local state"| db

	lan_note["trusted LAN target is not directly exposed publicly"]
	queue_note["backing-off head row blocks newer rows"]
	db_note["raw event acceptance precedes projections"]

	lan_note -.-> lan
	queue_note -.-> queue
	db_note -.-> db

	classDef edge fill:#eef6ff,stroke:#5b7fa6,color:#111827
	classDef public fill:#fff7e6,stroke:#a66f00,color:#111827
	classDef boundary fill:#f7f7f7,stroke:#666,color:#111827,stroke-dasharray: 4 4
	classDef trusted fill:#ecfdf3,stroke:#2f7d4f,color:#111827
	classDef storage fill:#f5f3ff,stroke:#6d5bd0,color:#111827
	classDef note fill:#ffffff,stroke:#999,color:#111827,stroke-dasharray: 3 3

	class shortcut,payload edge
	class webhook,auth,validate public
	class delivery boundary
	class accept,projections,enrich,operator,viewer trusted
	class queue,db storage
	class lan_note,queue_note,db_note note
```

Accuracy note: this is the production trust model. It intentionally omits real
hostnames, addresses, private topology, credentials, and roadmap inference
features. `/hook/homekit` is only a temporary migration compatibility alias and
is not shown as the canonical route.

## Place-State Transitions

The canonical state model separates action from place. Named places are
arbitrary lowercase slugs. `unnamed` is a real observed state outside all named
places; `null` means no observation or no known value.

```mermaid
stateDiagram-v2
	[*] --> Unnamed

	state "named place\narbitrary lowercase slug" as Named
	state "unnamed\nobserved outside named places" as Unnamed

	Named --> Unnamed: leave <place>
	Unnamed --> Named: arrive <place>

	state "Examples from public Chicago fixture" as Examples
	state Examples {
		state "sheridan-plaza" as SP
		state "unnamed" as U1
		state "unnamed" as U2
		state "kilmer-elementary" as KE

		SP --> U1: leave sheridan-plaza
		U2 --> KE: arrive kilmer-elementary
	}

	note right of Named
		event = arrive | leave
		place = lowercase slug | unnamed
	end note

	note left of Unnamed
		unnamed is a real observed state.
		null means no observation or no known value;
		it is not an operational place-state.
	end note
```

Accuracy note: legacy `previous_status` and `new_status` fields still exist for
compatibility, but they are not the canonical place-state model.

## Doorway Correlation

Raw doorway observations and phone-derived geofence transitions remain
independent records. Private read-only operator tooling builds two complementary
bounded views without rewriting either stream. Half-open windows prevent overlap;
unmatched anchors remain explicit rather than being forced into a conclusion.

```mermaid
flowchart LR
	subgraph observations["INDEPENDENT RAW OBSERVATIONS"]
		arrival["home-geofence arrival"]
		button_in["single doorway-button observation"]
		button_out["single doorway-button observation"]
		departure["home-geofence departure"]
	end

	subgraph operator["READ-ONLY OPERATOR CORRELATION"]
		arrival_window["arrival window<br/>[this home arrival, next home arrival)"]
		departure_window["departure window<br/>[this single press, next single press)"]
	end

	subgraph result["EXPLAINABLE RESULT"]
		arrival_result["first eligible press<br/>or unmatched"]
		departure_result["first eligible leave-home event<br/>or unmatched"]
	end

	arrival --> arrival_window
	button_in --> arrival_window
	arrival_window --> arrival_result

	button_out --> departure_window
	departure --> departure_window
	departure_window --> departure_result

	note1["windows are computed before limit<br/>matched observations are not reused"]
	note2["correlation is not causality<br/>raw streams remain distinct"]

	note1 -.-> operator
	note2 -.-> result

	classDef observed fill:#eef6ff,stroke:#5b7fa6,color:#111827
	classDef derived fill:#fff7e6,stroke:#a66f00,color:#111827
	classDef output fill:#ecfdf3,stroke:#2f7d4f,color:#111827
	classDef note fill:#ffffff,stroke:#999,color:#111827,stroke-dasharray: 3 3

	class arrival,button_in,button_out,departure observed
	class arrival_window,departure_window derived
	class arrival_result,departure_result output
	class note1,note2 note
```

Accuracy note: this diagram documents privately implemented behavior with
public-safe abstractions. It does not imply that the private `bin/presence`
implementation or operational database is included in this repository. A match
means only that the stated temporal rule selected an eligible counterpart.

## Local Demo Flow

The deterministic local demo exercises real implemented parsing,
authentication, durable queueing, strict oldest-row delivery, SQLite-first
acceptance, derived projections, and viewer reader compatibility. It uses a
demo-only local adapter where production uses the private delivery hop.

```mermaid
flowchart LR
	subgraph fixture["PUBLIC SYNTHETIC FIXTURES"]
		json["leave sheridan-plaza<br/>arrive kilmer-elementary"]
		token["non-secret demo token"]
	end

	subgraph loopback["LOOPBACK-ONLY LOCAL INGRESS"]
		webhook["real webhook handler<br/>/hook/presence"]
		auth["real authentication logic"]
		queue[("durable webhook queue")]
	end

	subgraph adapter["DEMO-ONLY ADAPTER"]
		drain["deliver oldest unfinished row"]
		call["invoke trusted-side script locally"]
	end

	subgraph trusted["REAL TRUSTED-SIDE PROCESSING"]
		eventsh["event.sh"]
		accept["SQLite-first acceptance"]
		db[("disposable presence.sqlite<br/>demo/tmp/")]
		state["derived projections"]
		viewer["existing viewer reader<br/>compatibility check"]
	end

	json -->|"POST to 127.0.0.1"| webhook
	token --> auth
	webhook --> auth
	auth --> queue
	queue --> drain
	drain --> call
	call --> eventsh
	eventsh --> accept
	accept --> db
	db --> state
	viewer -->|"reads generated rows"| db

	note1["production private-delivery transport is not simulated or claimed"]
	note2["async enrichment trigger disabled for deterministic local execution"]
	note3["no live or private infrastructure participates"]

	note1 -.-> adapter
	note2 -.-> accept
	note3 -.-> loopback

	classDef demo fill:#eef6ff,stroke:#5b7fa6,color:#111827
	classDef public fill:#fff7e6,stroke:#a66f00,color:#111827
	classDef boundary fill:#f7f7f7,stroke:#666,color:#111827,stroke-dasharray: 4 4
	classDef trusted fill:#ecfdf3,stroke:#2f7d4f,color:#111827
	classDef storage fill:#f5f3ff,stroke:#6d5bd0,color:#111827
	classDef note fill:#ffffff,stroke:#999,color:#111827,stroke-dasharray: 3 3

	class json,token public
	class webhook,auth demo
	class drain,call boundary
	class eventsh,accept,state,viewer trusted
	class queue,db storage
	class note1,note2,note3 note
```

Accuracy note: the demo is local-only, binds ingress to loopback, uses a
non-secret demo token, keeps runtime state under `demo/tmp/`, disables optional
weather lookup, and does not touch live infrastructure.
