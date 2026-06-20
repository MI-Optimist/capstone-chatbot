// Reads the user's input and selected mode, sends a POST request to the matching
// Flask endpoint, and delegates rendering to displayMessage().
// The three endpoints (/answer, /kbanswer, /search) mirror the three backend functions in app.py.
function sendMessage() {
    let messageInput = document.getElementById('message-input');
    let message = messageInput.value;
    displayMessage('user', message)
    
    // Get the selected function from the dropdown menu
    let functionSelect = document.getElementById('function-select');
    let selectedFunction = functionSelect.value;
    
    // Send an AJAX request to the Flask API endpoint based on the selected function
    let xhr = new XMLHttpRequest();
    let url;

    switch (selectedFunction) {
        case 'search':
            url = '/search';
            break;
        case 'kbanswer':
            url = '/kbanswer';
            break;
        case 'answer':
            url = '/answer';
            break;
        default:
            url = '/answer';
    }
    
    // show before sending
    document.getElementById('loading').style.display = 'block';
    // Clear the input field
    messageInput.value = 'The Brain is pondering...';

    xhr.open('POST', url);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function(){
        // hide inside xhr.onload before displaying response
        document.getElementById('loading').style.display = 'none';
        if (xhr.status == 200){
            let response = JSON.parse(xhr.responseText);
            displayMessage('assistant', response.message);
            // Clear the input field
            messageInput.value = '';
        }

    };
    xhr.onerror = function(){
        document.getElementById('loading').style.display='none';
        displayMessage('assistant', 'Error: Could not reach the server.');
    };
    xhr.send(JSON.stringify({message: message}));
    
}

// Creates a styled message bubble, labels it by sender, appends a timestamp,
// and auto-scrolls the chat container to the bottom.
// Uses createTextNode (not innerHTML) for the message body to avoid XSS from LLM output.
function displayMessage(sender, message) {
    let chatContainer = document.getElementById('chat-container');
    let messageDiv = document.createElement('div');

    if (sender === 'assistant') {
        messageDiv.classList.add('assistant-message');
        
        // Create a span for the Chatbot text
        let chatbotSpan = document.createElement('span');
        chatbotSpan.innerHTML = "<b>Chatbot:</b> ";
        messageDiv.appendChild(chatbotSpan);
        
        // Append the message to the Chatbot span
        //address html chars
        let textNode = document.createTextNode(message);
        messageDiv.appendChild(textNode);
    } else {
        messageDiv.classList.add('user-message');

        let userSpan = document.createElement('span');
        userSpan.innerHTML = "<b>User:</b> ";
        messageDiv.appendChild(userSpan);
        
        // Append the message to the span
        let textNode = document.createTextNode(message);
        messageDiv.appendChild(textNode);
    }

    // Create a timestamp element
    let timestamp = document.createElement('span');
    timestamp.classList.add('timestamp');
    let currentTime = new Date().toLocaleTimeString();
    timestamp.innerText = " ["+ currentTime+"]";
    messageDiv.appendChild(timestamp);

    chatContainer.appendChild(messageDiv);

    // Scroll to the bottom of the chat container
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Handle button click event
let sendButton = document.getElementById('send-btn');
sendButton.addEventListener('click', sendMessage);

document.getElementById('message-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendMessage();
});

document.getElementById('clear-btn').addEventListener('click', function() {
    document.getElementById('chat-container').innerHTML = '';
});
