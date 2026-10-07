# Campus Lost and Found

A school-based lost-and-found and second-hand trading platform built with Python Flask.

## Setup

```bash
pip install -r requirements.txt
python reset_db.py   # creates lostfound.db and seeds sample items
python app.py
```

Set the `SECRET_KEY` environment variable to a long random value in any non-development environment; the hardcoded fallback is for local development only.

## Item & Claim Status Lifecycle

Each item moves through three statuses, and each claim request (a user asking to claim an item) moves through its own set of statuses independently.

**Item status**

| Status | Badge shown | Meaning |
|---|---|---|
| `available` | *(none)*, or **Request pending** if someone has an open claim request | Open for anyone to send a claim request |
| `pending` | **Claim pending** | The poster has picked a requester as the rightful owner; locked — no one else can send new claim requests |
| `claimed` | **Claimed** | The poster has confirmed the item was actually handed over; final |

**Claim request status** (per requester, per item)

| Status | Meaning |
|---|---|
| `pending` | Sent, awaiting the poster's decision |
| `confirmed` | The poster picked this requester as the rightful owner |
| `declined` | Another requester was confirmed instead |
| `cancelled` | The requester withdrew their own request |

**Flow**

1. A poster lists an item — it starts out `available`.
2. Any logged-in user (other than the poster) can send a claim request. The item stays `available` and multiple people can request it at the same time (shown as "Request pending"). A requester can cancel their own pending request at any time (with a confirmation prompt); this doesn't affect anyone else's request and they're free to send a new one later.
3. The poster reviews the open requests on the item page and clicks **Confirm requester** on whichever one they believe is the rightful owner. This confirms that request, declines all the other open ones for that item, and moves the item to `pending` ("Claim pending") — at this point nobody else can send new requests.
4. The poster and the confirmed requester are expected to arrange the actual hand-off themselves outside the app (by email — see below). The app doesn't track this step.
5. Once the hand-off has happened, the poster clicks **Confirm claimed**, which moves the item to `claimed`. This is the final state.

**Contact visibility:** a user's email and availability on their profile page are private by default. They become visible to another user only once the two of them have exchanged a claim request on some item (in either direction) — that's what lets a poster and requester coordinate a meet-up by email.

## Known Limitations

### User Role Detection
Currently, users self-select their role (Student or Teacher) during registration via a dropdown. The ideal solution would be to automatically identify a user's role by cross-referencing their email or student/staff ID against the school's own database or directory — but this has not been implemented yet due to the following challenges:

- Schools in the UK do not follow a single standard email domain pattern, making domain-based detection unreliable
- Some schools do not assign student/staff IDs at all
- Accessing a school's internal database would require integration with their IT systems, which varies greatly between institutions

**Planned improvement:** Investigate school-specific APIs or directory services (e.g. Microsoft Entra ID / Azure AD, which many UK schools already use for Office 365) that could verify a user's role automatically at sign-up.