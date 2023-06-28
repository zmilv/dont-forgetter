[![CI](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml)
[![CD](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml)
<div align="center"><img src="https://github.com/zmilv/dont-forgetter/assets/27917439/9dc5b3db-7fac-4c1c-9611-f9e956ff8352)" /></div>

# dont-forgetter

>Browsable API link: https://dont-forgetter.rest \
>Swagger documentation: https://dont-forgetter.rest/docs/

The dont-forgetter API is a tool designed to help users schedule notifications and reminders for important events. Developed with the intention of preventing forgetfulness, this API allows me (and you!) to conveniently schedule notifications for birthdays, assignments or any other events that preferably would not be missed.

The API can be used to integrate reminder and note-taking functionalities into other applications. It can also be used as a standalone service via the browsable API link. By utilising the available endpoints, you can easily schedule, retrieve, and manage events and notes.

By default, all users receive 20 free email notifications and 10 free SMS notifications per month. However, please don't hesitate to reach out if you require a higher limit. :)

Happy remembering!

### Features
- Schedule notifications or reminders to be sent at a chosen date and time.
- Support for periodic events, ensuring recurring reminders are never missed.
- Currently available notification types: email and SMS.
- Store and manage notes to keep track of important information.
- Query events and notes using GET requests with various operators (equal, and, or, not, greater_than, less_than).
- Edit or delete existing notes and events.
- Categorize notes and events for better organization.

---

## API usage
#### Authentication
If using the API via browser, Django session authentication will be used.
Otherwise, JWT bearer token needs to be provided in request headers.
#### User endpoints
- PATCH /user - edit user details
- GET /user - get user details
- POST /user/settings - edit user settings
- GET /user/settings - get user settings
- POST /user/register/ - register an account
- POST /user/login/ - log into an account and get a JWT
- POST /user/token/refresh/ - refresh a JWT
- POST /user/logout/ - log out of an account
#### Event endpoints
- POST event/ - add or edit an event (if 'id' provided)
- GET event/ - get details about the closest events
- GET event/?query=\<query\> - get details about events matching the query
- GET event/\<int:id\>/ - get details about a specific event
- DELETE event/\<int:id\>/ - delete a specific event
#### Note endpoints
- POST note/ - add or edit a note (if 'id' provided)
- GET note/ - get details about the latest notes
- GET note/?query=\<query\> - get details about notes matching the query
- GET note/\<int:id\>/ - get details about a specific note
- DELETE note/\<int:id\>/ - delete a specific note

### Queries
| Operator     | Examples                                            |
|--------------|-----------------------------------------------------|
| equal        | equal(type,"birthday")                              |
| and          | and(equal(type,"uni"),less_than(date,"2023-05-16")) |
| or           | or(equal(type,"uni"),equal(type,"work"))            |
| not          | not(equal(type,"uni"))                              |
| greater_than | greater_than(date,"2023-06-01")                     |
| less_than    | less_than(time,"17:00")                             |

### Event fields
| Field             | Type                | Examples            |
|-------------------|---------------------|---------------------|
| id                | integer (read-only) |                     |
| notification_type | string              | "email", "sms"      |
| category          | string              | "birthday", "uni"   |
| title             | string (required)   |                     |
| date              | string (required)   | "2023-05-15"        |
| time              | string              | "14:00"             |
| notice_time       | string              | "15min", "2h", 1d"  |
| interval          | string              | "15min", "2h", 1d"  |
| info              | string              |                     |
| utc_offset        | string              | "+2", "+0", "-3:30" |

### Note fields
| Field      | Type                | Examples           |
|------------|---------------------|--------------------|
| id         | integer (read-only) |                    |
| category   | string              |                    |
| title      | string (required)   |                    |
| info       | string (required)   |                    |
| created_at | string (read-only)  | "2023-05-15 14:00" |
| updated_at | string (read-only)  | "2023-05-15 14:00" |

### User fields
| Field        | Type              | Examples          |
|--------------|-------------------|-------------------|
| username     | string (required) |                   |
| e-mail       | string (required) | "name@email.com"  |
| phone_number | string            | "37069935951"     |

### User Settings fields
| Field                     | Type   | Examples            |
|---------------------------|--------|---------------------|
| default_notification_type | string | "email", "sms"      |
| default_time              | string | "14:00"             |
| default_utc_offset        | string | "+2", "+0", "-3:30" |


---

### Local set-up
1. ```git clone```
2. Create .env.dev out of .env.template
3. Enter your notification API credentials into .env.dev
4. Get the docker image running ```docker-compose up --build```

---

### Current architecture
![df-architecture](https://github.com/zmilv/dont-forgetter/assets/27917439/ba7a3a3f-610c-47c5-8fc0-75028043c5ef)

---

### Future plans
- Account for daylight savings (by location)
- Email and phone number verification
- Encryption
- More notification types
- React Native front-end
