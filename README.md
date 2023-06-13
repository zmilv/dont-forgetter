[![CI](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/ci.yml)
[![CD](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml/badge.svg)](https://github.com/zmilv/dont-forgetter/actions/workflows/cd.yml)

# dont-forgetter (WIP)

Live link: https://dont-forgetter.rest

The application provides a RESTful API that allows users to create notes and set reminders for specific dates and times. Users can choose the type of notification they prefer, such as email, ~~SMS or Discord message~~ (coming soon) and the application will send the notification at the scheduled time. 

In addition, the API supports CRUD operations for notes, allowing users to create, retrieve, update, and delete notes as needed. The API also provides an endpoint to view upcoming reminders, as well as the ability to edit or delete them. The reminders and notes can be organized into categories for easier management. Authentication is supported to ensure secure access to the user's data.

This application can be useful for a variety of scenarios, such as personal to-do lists, project management, and team collaboration. With its flexible API, developers can easily integrate it into other applications or services. 


### Local set-up
1. ```git clone```
2. Enter your SMTP e-mail credentials in env_vars/.env.docker
3. Get the docker image running ```docker-compose up --build```

>### API usage
> #### Authentication
> If using the API via browser, Django session authentication will be used.
> Otherwise, JWT bearer token needs to be provided in request headers.
> #### Account endpoints
> - POST register/ - register an account
> - POST login/ - log into an account and get a JWT
> - POST token/refresh/ - refresh a JWT
> - POST logout/ - log out of an account
> #### Event endpoints
> - POST event/ - add an event
> - GET event/ - get details about the closest events
> - GET event/\<int:id\>/ - get details about a specific event
> - GET event/?query=\<query\> - get details about events matching the query
> - DELETE event/\<int:id\>/ - delete a specific event
> #### Note endpoints
> - POST note/ - add a note
> - GET note/ - get details about the latest notes
> - GET note/\<int:id\>/ - get details about a specific note
> - GET note/?query=\<query\> - get details about notes matching the query
> - DELETE note/\<int:id\>/ - delete a specific note

### Event fields
| Field       | Type                | Examples            |
|-------------|---------------------|---------------------|
| id          | integer (automatic) |                     |
| category    | string              | "birthday", "uni"   |
| title       | string (required)   |                     |
| date        | string (required)   | "2023-05-15"        |
| time        | string              | "14:00"             |
| notice_time | string              | "15min", "1d"       |
| interval    | string              | "15min", "1d"       |
| info        | string              |                     |
| utc_offset  | string              | "+2", "+0", "-3:30" |

### Note fields
| Field      | Type                | Examples           |
|------------|---------------------|--------------------|
| id         | integer (automatic) |                    |
| category   | string              |                    |
| title      | string (required)   |                    |
| info       | string (required)   |                    |
| created_at | string (automatic)  | "2023-05-15 14:00" |
| updated_at | string (automatic)  | "2023-05-15 14:00" |

### Queries
| Operator     | Examples                                                |
|--------------|---------------------------------------------------------|
| equal        | equal(category,"birthday")                              |
| and          | and(equal(category,"uni"),less_than(date,"2023-05-16")) |
| or           | or(equal(category,"uni"),equal(category,"work"))        |
| not          | not(equal(category,"uni"))                              |
| greater_than | greater_than(date,"2023-06-01")                         |
| less_than    | less_than(time,"17:00")                                 |

### Current architecture
![df-current-architecture_k30lF0D](https://github.com/zmilv/dont-forgetter/assets/27917439/87dcd5c5-b97d-48a0-844c-c1bff60c89d4)

### Future plans
- React Native front-end
- More notification types
