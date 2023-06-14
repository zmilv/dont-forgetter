[![CI](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml)
[![CD](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml)

# dont-forgetter (WIP)

>Browsable API link: https://dont-forgetter.rest\
>Swagger documentation: https://dont-forgetter.rest/docs/

The application provides a RESTful API that allows users to create notes and set reminders for specific dates and times. Users can choose the type of notification they prefer, such as email, ~~SMS, Discord message, or push notification~~ (coming soon) and the application will send the notification at the scheduled time. 

In addition, the API supports CRUD operations for notes, allowing users to create, retrieve, update, and delete notes as needed. The API also provides an endpoint to view upcoming reminders, as well as the ability to edit or delete them. The reminders and notes can be organized into types for easier management. Authentication is supported to ensure secure access to the user's data.

This application can be useful for a variety of scenarios, such as personal to-do lists, project management, and team collaboration. With its flexible API, developers can easily integrate it into other applications or services. 

---

## API usage
#### Authentication
If using the API via browser, Django session authentication will be used.
Otherwise, JWT bearer token needs to be provided in request headers.
#### Account endpoints
- POST register/ - register an account
- POST login/ - log into an account and get a JWT
- POST token/refresh/ - refresh a JWT
- POST logout/ - log out of an account
#### Event endpoints
- POST event/ - add an event
- GET event/ - get details about the closest events
- GET event/?query=\<query\> - get details about events matching the query
- GET event/\<int:id\>/ - get details about a specific event
- DELETE event/\<int:id\>/ - delete a specific event
#### Note endpoints
- POST note/ - add a note
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
| id                | integer (automatic) |                     |
| notification_type | string              | "email", "sms"      |
| category          | string              | "birthday", "uni"   |
| title             | string (required)   |                     |
| date              | string (required)   | "2023-05-15"        |
| time              | string              | "14:00"             |
| notice_time       | string              | "15min", "1d"       |
| interval          | string              | "15min", "1d"       |
| info              | string              |                     |
| utc_offset        | string              | "+2", "+0", "-3:30" |

### Note fields
| Field      | Type                | Examples           |
|------------|---------------------|--------------------|
| id         | integer (automatic) |                    |
| category   | string              |                    |
| title      | string (required)   |                    |
| info       | string (required)   |                    |
| created_at | string (automatic)  | "2023-05-15 14:00" |
| updated_at | string (automatic)  | "2023-05-15 14:00" |

---

### Local set-up
1. ```git clone```
2. Copy .env.dev.template into .env.dev
3. Enter your SMTP e-mail credentials into .env.dev
4. Get the docker image running ```docker-compose up --build```

---

### Current architecture
![df-current-architecture_k30lF0D](https://github.com/zmilv/dont-forgetter/assets/27917439/87dcd5c5-b97d-48a0-844c-c1bff60c89d4)

---

### Future plans
- React Native front-end
- More notification types
