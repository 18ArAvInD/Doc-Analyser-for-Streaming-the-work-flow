// File Handling Functions
const importFile = () => {
    const fileInput = document.getElementById("fileInput");
    fileInput.click();
}

const extractStructuredData = () => {
    const formData = new FormData(document.getElementById("uploadForm"));

    fetch("/extract_and_store", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            alert("File uploaded successfully and parsed content stored in the database!");
        }
    })
    .catch(error => console.error("Error:", error));
}

const parseDocument = () => {
    const formData = new FormData(document.getElementById("uploadForm"));

    fetch("/analyze", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            // Redirect to parse.html with the parsed content ID
            window.location.href = `/parse/${data.parsed_content_id}`;
        }
    })
    .catch(error => console.error("Error:", error));
}

// User Authentication Functions
const registerUser = () => {
    const { firstname, lastname, email, password } = getUserRegistrationData();

    fetch("/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            firstname,
            lastname,
            email,
            password
        })
    })
    .then(handleRegistrationResponse)
    .catch(handleError);
}

const loginUser = () => {
    const { email, password } = getUserLoginData();

    fetch("/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email,
            password
        })
    })
    .then(handleLoginResponse)
    .catch(handleError);
}

// Helper Functions
const getUserRegistrationData = () => {
    const firstname = document.getElementById("firstname").value;
    const lastname = document.getElementById("lastname").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    return { firstname, lastname, email, password };
}

const getUserLoginData = () => {
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    return { email, password };
}

const handleRegistrationResponse = (response) => {
    if (response.ok) {
        alert("Registration successful. You can now log in.");
        window.location.href = "/login";
    } else {
        alert("Registration failed. Please try again.");
    }
}

const handleLoginResponse = (response) => {
    if (response.ok) {
        window.location.href = "/index";
    } else {
        response.json().then(data => {
            alert(data.error);
        });
    }
}

const handleError = (error) => {
    console.error("Error:", error);
    alert("An error occurred while processing your request. Please try again later.");
}
