## v1

In the backend api/mv/generate_character_reference to accept a request for 1-4 generated images on the same prompt and modify the replicate api service call to also do this, and modify the response from the python api to pass the frontend all the character_ref_xxx ids.
In the frontend for generate character reference enable the display of 4 simulataeous character reference images and allow the user to select one and only one of those references to proceed to the next step.

## v2

Let's add another button to the front end on the create page below the "Generate videos" button. this new button is called "Quick Job" and it will operate simliar to "generate videos" by routing to a new page of route /quick-gen-page instead of result/job_<id>. But this button will have no validation logic for being enabled.

This page should utilize the layout and styling of the result/job_<id> page but this should send the data from the create page onto the second page and display:
- the "video description"
- the "character and style"
- the id of the character reference image.
These fields should de displayed in a card on that page above the other sections. Don't worry about styling these, in future these fields will be used as payloads in requests to the backend from that /quick-gen-page.