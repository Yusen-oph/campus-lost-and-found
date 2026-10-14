# Campus Lost and Found

A school-based lost-and-found and second-hand trading platform built with Python Flask.

## Setup

```bash
pip install -r requirements.txt
python reset_db.py   # creates lostfound.db and seeds sample items
python app.py
```

Set the `SECRET_KEY` environment variable to a long random value in any non-development environment; the hardcoded fallback is for local development only.

Uploaded photos (item photos and profile photos) are saved in `static/uploads/`, which is not tracked by Git.

`python app.py` runs the app in development mode. When the app is started any other way (for example by a web host importing `app.py`), it counts as running online: it refuses to start unless `SECRET_KEY` is set, and the login cookie is only sent over HTTPS.

## Running it on PythonAnywhere

1. In a PythonAnywhere **Bash console**: `git clone https://github.com/Yusen-oph/campus-lost-and-found.git`, then `cd campus-lost-and-found`, `pip install --user -r requirements.txt` and `python init_db.py` (creates an empty database).
2. On the **Web** tab: *Add a new web app* → *Manual configuration* → the same Python version as the console. Set *Source code* to `/home/<username>/campus-lost-and-found`.
3. Edit the **WSGI configuration file** linked on the Web tab so it contains:
   ```python
   import os, sys
   os.environ["SECRET_KEY"] = "<a long random value>"
   project = "/home/<username>/campus-lost-and-found"
   if project not in sys.path:
       sys.path.insert(0, project)
   from app import app as application
   ```
4. Under **Static files**, map URL `/static/` to `/home/<username>/campus-lost-and-found/static`.
5. Turn on **Force HTTPS**, then click **Reload**.

To update the site later: `git pull` in the console, then **Reload** on the Web tab.

## Features

- **Accounts:** sign up (password of at least 8 characters, optional profile photo) and log in. "Remember me" keeps you logged in for 30 days; otherwise you're logged out when the browser closes.
- **Profiles:** your profile shows your photo (or initials), role, school and availability. You can change or remove your photo and edit your availability (up to 500 characters) on your own profile.
- **Posting items:** list a lost, found or trade item with an optional photo (PNG, JPG, GIF or WEBP, up to 5 MB). Click a photo on an item page to view it full-screen.
- **Editing and deleting posts:** owners can edit or delete their own posts, with these limits:
  - a post can't be deleted while it has pending claim requests (decline them or wait for them to be cancelled first);
  - a post can't be edited or deleted once a claimant has been confirmed.
- **Claiming:** see the lifecycle below.
- **Notifications:** the bell shows requests on your items and updates on your own requests. Each one can be deleted with its × button.
- **Dark mode:** the moon/sun button switches between light and dark. First-time visitors get their device's setting; after that, their choice is remembered in the browser.
- **Phones:** the layout works down to 320px wide.

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
| `rejected` | The poster turned this request down with **Decline** |
| `cancelled` | The requester withdrew their own request |

**Flow**

1. A poster lists an item — it starts out `available`.
2. Any logged-in user (other than the poster) can send a claim request. The item stays `available` and multiple people can request it at the same time (shown as "Request pending"). A requester can cancel their own pending request at any time (with a confirmation prompt); this doesn't affect anyone else's request.
3. Each user can send **at most 3 requests per item**. Every request counts, including ones they cancelled themselves and ones that were declined. The item page shows how many attempts are left; after the third, the request form is replaced by a message saying they can't request that item again.
4. The poster reviews the open requests on the item page. They can click **Decline** on a request they don't accept (the requester is notified that it was declined), or **Confirm requester** on whichever one they believe is the rightful owner. This confirms that request, declines all the other open ones for that item, and moves the item to `pending` ("Claim pending") — at this point nobody else can send new requests.
5. The poster and the confirmed requester are expected to arrange the actual hand-off themselves outside the app (by email — see below). The app doesn't track this step.
6. Once the hand-off has happened, the poster clicks **Confirm claimed**, which moves the item to `claimed`. This is the final state.

**Contact visibility:** a user's email and availability on their profile page are private by default. They become visible to another user only once the two of them have exchanged a claim request on some item (in either direction) — that's what lets a poster and requester coordinate a meet-up by email.

## Known Limitations

### No password reset
There is no "forgot password" feature yet. A reset normally works by emailing the user a link, which needs an email-sending service to be set up first.

### Settings saved per browser
The dark/light choice and which notifications have been seen are stored in the browser, not the account, so they don't follow a user to another device and are shared by anyone using the same browser.

### User Role Detection
Currently, users self-select their role (Student or Teacher) during registration via a dropdown. The ideal solution would be to automatically identify a user's role by cross-referencing their email or student/staff ID against the school's own database or directory — but this has not been implemented yet due to the following challenges:

- Schools in the UK do not follow a single standard email domain pattern, making domain-based detection unreliable
- Some schools do not assign student/staff IDs at all
- Accessing a school's internal database would require integration with their IT systems, which varies greatly between institutions

**Planned improvement:** Investigate school-specific APIs or directory services (e.g. Microsoft Entra ID / Azure AD, which many UK schools already use for Office 365) that could verify a user's role automatically at sign-up.