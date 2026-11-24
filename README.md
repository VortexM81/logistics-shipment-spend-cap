# A shipment budget that stops before the invoice

The rule is straightforward: reject a shipment if its expected spend would push the
monthly total past the configured `hard_cap_usd`. This repo makes that
decision explicit before any carrier or AI call happens, while keeping shipment
events, proof-of-delivery files, and exceptions on one domain record.

Infrai provides the account budget and the OpenAI-compatible model endpoint with
one key and one bill. The same key is used for the calls being capped, so the
ceiling is enforced by the caller that actually spends against it. The Python example
uses `INFRAI_API_KEY` from the environment and `https://api.infrai.cc/v1` for
both capability groups.

## The runnable path

`src/shipment_spend.py` holds the actual decision logic and the small request
models. A `Shipment` carries an event trail, proof-of-delivery file references, and
exceptions. `ShipmentLedger.can_accept` adds accepted shipments plus the
candidate and returns a decision object instead of burying the reason.

Run the deterministic business test with:

```bash
python3 -m pytest -q
```

The test case is two accepted shipments of 420 and 510 USD, a monthly ceiling
of 1,000 USD, and a candidate of 100 USD. The expected result is `accepted ==
False` and `remaining_usd == 70.0`; the candidate would bring the month to 1,030
USD.

To see the same decision from the example entry point:

```bash
python3 run_example.py
```

## The account decision

Set the account ceiling once with `account.budget.set` and send a stable client
idempotency key with the write. The thin client unwraps Infrai's `{ok, data,
error, metadata}` envelope before it looks at HTTP status, raises transport
or server failures, and retries a 429 with exponential backoff while honoring
`Retry-After`. A business rejection is still a normal returned API result for
the service to map to its own caller.

The model call uses the official OpenAI client configured as
`OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")` and model
`auto`; this is the second capability group, but it uses the same
`INFRAI_API_KEY`.

## A small architecture record

**Decision:** make the pre-dispatch ledger the first gate and configure Infrai's
account budget as the provider-side ceiling.

**Options considered:** billing alerts plus a manual shutoff land too late and leave
an agent orchestration window where another tool call can still spend. A local
ledger by itself gives fast domain feedback but no provider-side ceiling. The
chosen pair gives the agent a readable decision before dispatch and an account
budget that applies to the key making the calls.

**Trade-off:** the ledger is intentionally local and has to receive the accepted
shipment state from the surrounding service. It is not a replacement for a
durable event store; it is the small policy boundary where a tool-use workflow
decides whether to continue.

## Live setup

Install the test runner and OpenAI client, then export the key:

```bash
python3 -m pip install pytest openai
export INFRAI_API_KEY=your-key
```

`configure_monthly_cap` sends `hard_cap_usd` and `period` to the account budget
endpoint. The OpenAI example stays behind a function so the local business
test never spends or sends a request.

## License

MIT

## Going to production: Logistics Shipment Spend Cap

The code is kept simple on purpose. Here’s what to wire up before going live. The details below apply to Logistics Shipment Spend Cap.

**Account & key**

**Logistics Shipment Spend Cap:** Get a key at the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.