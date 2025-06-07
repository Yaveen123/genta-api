# Welcome to Genta API!
I am just a student, and there are most definitely vulnerabilities or areas for improvement! If so, could you please let me know asap! Thank you so much :D

> [!NOTE]  
> Genta is still in alpha.


|  | ➡️ Backend Microservice ⬅️ | Frontend Microservice | 
| - | ---------------------| -----------------------|
| _Branding image_ |  ![Frame 69372](https://github.com/user-attachments/assets/2cacf5a7-d310-49d0-bf8c-f2492b1077b7)  |  ![Frame 69371](https://github.com/user-attachments/assets/5887b990-1b86-4ec8-b353-1f2c67fac721) |
| _Description_ | For the frontend to retrieve/update data, it pings API endpoints that run on this. | The frontend presents the content from the backend in a way that's accessible to the user. | 
| _Deployed URL_ | https://genta-api.online | https://genta.live | 
| _Repository_ | https://github.com/yaveen123/genta-api |  https://github.com/yaveen123/genta-general |  


## API routes
> [!TIP]
> The API may still have bugs or problems.
> If you find anything please let me know!

| Route | Description |
| - | - |
| https://genta-api.online/verify_user | Checks if JWT in auth header passes, returns 200 if successfully authorised. Used by client to check if JWT is still valid. | 
| https://genta-api.online/get-data | Returns user data as JSON. Users are identified Google account sub returned when verifying JWT. | 
| https://genta-api.online/update-data | Edits user data on database through reading the JSON within the payload of the request. |

