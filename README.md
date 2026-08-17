# Campus Lost and Found

A school-based lost-and-found and second-hand trading platform built with Python Flask.

## Known Limitations

### User Role Detection
Currently, users self-select their role (Student or Teacher) during registration via a dropdown. The ideal solution would be to automatically identify a user's role by cross-referencing their email or student/staff ID against the school's own database or directory — but this has not been implemented yet due to the following challenges:

- Schools in the UK do not follow a single standard email domain pattern, making domain-based detection unreliable
- Some schools do not assign student/staff IDs at all
- Accessing a school's internal database would require integration with their IT systems, which varies greatly between institutions

**Planned improvement:** Investigate school-specific APIs or directory services (e.g. Microsoft Entra ID / Azure AD, which many UK schools already use for Office 365) that could verify a user's role automatically at sign-up.