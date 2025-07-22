const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const fileBtn = document.getElementById('fileBtn');
const fileInput = document.getElementById('fileInput');

let isStreaming = false;
let uploadedFile = null;

// Add message to chat
function addMessage(content, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return messageDiv;
}

// Add file info display
function addFileInfo(fileName, fileSize) {
    const fileInfoDiv = document.createElement('div');
    fileInfoDiv.className = 'file-info';
    fileInfoDiv.innerHTML = `
        📄 <span class="file-name">${fileName}</span>
        <span class="file-size">(${formatFileSize(fileSize)})</span>
    `;
    messagesDiv.appendChild(fileInfoDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return fileInfoDiv;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle file selection
function handleFileSelection() {
    const file = fileInput.files[0];
    if (!file) return;
    
    // Check file size (limit to 10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        fileInput.value = '';
        return;
    }
    
    uploadedFile = file;
    addFileInfo(file.name, file.size);
    messageInput.placeholder = `File selected: ${file.name}. Type a message or press Send to analyze the file.`;
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    
    // Check if we have a message or a file
    if ((!message && !uploadedFile) || isStreaming) return;
    
    // Disable input
    isStreaming = true;
    sendBtn.disabled = true;
    fileBtn.disabled = true;
    
    try {
        let finalMessage = message;
        
        // Handle file upload
        if (uploadedFile) {
            // Add user message showing file upload
            const fileMessage = message ? 
                `${message}\n\n📄 Uploaded file: ${uploadedFile.name}` : 
                `📄 Analyze this file: ${uploadedFile.name}`;
            addMessage(fileMessage, true);
            
            // Upload file first
            const formData = new FormData();
            formData.append('file', uploadedFile);
            if (message) formData.append('message', message);
            
            const uploadResponse = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                throw new Error('File upload failed');
            }
            
            const uploadResult = await uploadResponse.json();
            finalMessage = uploadResult.content || 'Please analyze this file.';
            
            // Clear file after upload
            uploadedFile = null;
            fileInput.value = '';
            messageInput.placeholder = 'Type your message or upload a file...';
        } else {
            // Regular text message
            addMessage(message, true);
        }
        
        messageInput.value = '';
        
        // Add assistant message container
        const assistantDiv = document.createElement('div');
        assistantDiv.className = 'message assistant';
        messagesDiv.appendChild(assistantDiv);
        
        // Use EventSource for Server-Sent Events
        const eventSource = new EventSource('/chat/stream?' + new URLSearchParams({
            message: finalMessage
        }));
        
        let assistantMessage = '';
        let renderTimeout = null;
        let lastRenderLength = 0;
        let lastRenderTime = 0;
        
        // Function to render markdown progressively
        function renderProgressiveMarkdown() {
            const now = Date.now();
            
            // Skip if we rendered very recently and content hasn't changed much
            if (now - lastRenderTime < 10 && assistantMessage.length - lastRenderLength < 3) {
                return;
            }
            
            try {
                // Parse the current markdown content
                const renderedContent = marked.parse(assistantMessage);
                assistantDiv.innerHTML = renderedContent + '<span class="cursor">▌</span>';
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                lastRenderLength = assistantMessage.length;
                lastRenderTime = now;
            } catch (e) {
                // If markdown parsing fails (incomplete structure), try partial rendering
                try {
                    // Attempt to render what we can by adding temporary closing tags for incomplete structures
                    let tempContent = assistantMessage;
                    
                    // Count unclosed code blocks and try to close them temporarily
                    const codeBlockMatches = tempContent.match(/```/g);
                    if (codeBlockMatches && codeBlockMatches.length % 2 === 1) {
                        tempContent += '\n```';
                    }
                    
                    // Count unclosed inline code and try to close them
                    const inlineCodeMatches = tempContent.match(/(?<!\\)`/g);
                    if (inlineCodeMatches && inlineCodeMatches.length % 2 === 1) {
                        tempContent += '`';
                    }
                    
                    const renderedContent = marked.parse(tempContent);
                    assistantDiv.innerHTML = renderedContent + '<span class="cursor">▌</span>';
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    lastRenderLength = assistantMessage.length;
                    lastRenderTime = now;
                } catch (e2) {
                    // If all else fails, show raw text with cursor
                    assistantDiv.innerHTML = assistantMessage.replace(/\n/g, '<br>') + '<span class="cursor">▌</span>';
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    lastRenderLength = assistantMessage.length;
                    lastRenderTime = now;
                }
            }
        }
        
        // Optimized render scheduling
        function scheduleRender() {
            if (renderTimeout) {
                clearTimeout(renderTimeout);
            }
            
            // Immediate render for significant content changes, word boundaries, or start of content
            const contentDelta = assistantMessage.length - lastRenderLength;
            const isWordBoundary = assistantMessage.endsWith(' ') || assistantMessage.endsWith('\n');
            
            if (contentDelta > 10 || assistantMessage.length < 20 || isWordBoundary) {
                renderProgressiveMarkdown();
                return;
            }
            
            // Use requestAnimationFrame for smooth rendering
            renderTimeout = setTimeout(() => {
                requestAnimationFrame(renderProgressiveMarkdown);
            }, 8);
        }
        
        eventSource.onmessage = function(event) {
            if (event.data === '[DONE]') {
                // Clear any pending render timeout
                if (renderTimeout) {
                    clearTimeout(renderTimeout);
                    renderTimeout = null;
                }
                // Render final markdown without cursor
                assistantDiv.innerHTML = marked.parse(assistantMessage);
                eventSource.close();
                // Re-enable input
                isStreaming = false;
                sendBtn.disabled = false;
                fileBtn.disabled = false;
                messageInput.focus();
                return;
            }
            
            try {
                const parsed = JSON.parse(event.data);
                if (parsed.content) {
                    // Handle regular text content (backward compatibility)
                    assistantMessage += parsed.content;
                    // Schedule progressive markdown rendering
                    scheduleRender();
                } else if (parsed.type === 'text' && parsed.content) {
                    // Handle new text format
                    assistantMessage += parsed.content;
                    // Schedule progressive markdown rendering
                    scheduleRender();
                } else if (parsed.file || (parsed.type === 'file' && parsed.file_info)) {
                    // Handle file (image) display
                    const fileInfo = parsed.file || parsed.file_info;
                    console.log('Received file info:', fileInfo); // Debug log
                    if (fileInfo.is_image) {
                        // Add image to the chat
                        const imageDiv = document.createElement('div');
                        imageDiv.className = 'image-container';
                        imageDiv.innerHTML = `
                            <img src="${fileInfo.relative_path}" 
                                 alt="${fileInfo.attachment_name}" 
                                 class="generated-image"
                                 loading="lazy" 
                                 onerror="console.error('Image failed to load:', '${fileInfo.relative_path}')" />
                            <p class="image-caption">${fileInfo.attachment_name}</p>
                        `;
                        messagesDiv.appendChild(imageDiv);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        console.log('Added image with src:', fileInfo.relative_path); // Debug log
                    } else {
                        // Handle non-image files
                        assistantMessage += `\n\n📎 Generated file: [${fileInfo.file_name}](${fileInfo.relative_path})\n`;
                        assistantDiv.innerHTML = assistantMessage + '<span class="cursor">▌</span>';
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                } else if (parsed.error) {
                    // Clear any pending render timeout
                    if (renderTimeout) {
                        clearTimeout(renderTimeout);
                        renderTimeout = null;
                    }
                    assistantDiv.textContent = `Error: ${parsed.error}`;
                    assistantDiv.style.color = '#dc3545';
                    eventSource.close();
                    isStreaming = false;
                    sendBtn.disabled = false;
                    fileBtn.disabled = false;
                    messageInput.focus();
                }
            } catch (e) {
                console.error('JSON parse error:', e);
            }
        };
        
        eventSource.onerror = function(event) {
            console.error('EventSource failed:', event);
            // Clear any pending render timeout
            if (renderTimeout) {
                clearTimeout(renderTimeout);
                renderTimeout = null;
            }
            assistantDiv.textContent = 'Connection error';
            assistantDiv.style.color = '#dc3545';
            eventSource.close();
            isStreaming = false;
            sendBtn.disabled = false;
            fileBtn.disabled = false;
            messageInput.focus();
        };
        
    } catch (error) {
        // Handle upload or streaming errors
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant';
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.color = '#dc3545';
        messagesDiv.appendChild(errorDiv);
        
        isStreaming = false;
        sendBtn.disabled = false;
        fileBtn.disabled = false;
        messageInput.focus();
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// File upload event listeners
fileBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', handleFileSelection);

// Focus input on load
messageInput.focus();
