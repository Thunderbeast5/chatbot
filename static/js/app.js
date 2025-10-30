// Global variables
let sessionId = generateSessionId();
let currentMap = null;
let userContext = {}; // Store user context for info panel sync
let userLocation = null; // Store user's GPS location

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Detect user's real location on page load
async function detectUserLocation() {
    // Try browser geolocation first
    if ('geolocation' in navigator) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                });
            });
            
            const { latitude, longitude } = position.coords;
            console.log('GPS Location detected:', latitude, longitude);
            
            // Send to backend to get city name
            const response = await fetch('/api/location/detect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude,
                    session_id: sessionId
                })
            });
            
            const data = await response.json();
            if (data.success && data.location) {
                userLocation = data.location;
                console.log('Location:', data.location.city, data.location.state);
                
                // Update context
                userContext.location = data.location.city;
                userContext.location_data = data.location;
                
                // Show location hint
                showLocationHint(data.location.city);
            }
        } catch (error) {
            console.log('GPS location denied or failed, using IP-based location');
            // Fallback to IP-based location
            await detectLocationFromIP();
        }
    } else {
        console.log('Geolocation not supported, using IP-based location');
        await detectLocationFromIP();
    }
}

// Fallback: Detect location from IP
async function detectLocationFromIP() {
    try {
        const response = await fetch('/api/location/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        if (data.success && data.location) {
            userLocation = data.location;
            console.log('IP Location:', data.location.city);
            
            // Update context
            userContext.location = data.location.city;
            userContext.location_data = data.location;
            
            showLocationHint(data.location.city);
        }
    } catch (error) {
        console.error('Location detection failed:', error);
    }
}

// Show location hint
function showLocationHint(city) {
    const hint = document.createElement('div');
    hint.className = 'location-hint';
    hint.innerHTML = `📍 Detected your location: <strong>${city}</strong> - We'll show businesses near you!`;
    hint.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.5s ease-out;
        font-size: 14px;
    `;
    
    document.body.appendChild(hint);
    
    // Remove after 5 seconds
    setTimeout(() => {
        hint.style.animation = 'slideOut 0.5s ease-out';
        setTimeout(() => hint.remove(), 500);
    }, 5000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    detectUserLocation();
});

// Handle enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Display user message
    addMessage(message, 'user');
    input.value = '';
    
    // Show loading
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        removeMessage(loadingId);
        
        // Update context
        if (data.context) {
            userContext = { ...userContext, ...data.context };
            updateInfoPanelContext();
        }
        
        // Display bot response
        displayResponse(data);
        
    } catch (error) {
        console.error('Error:', error);
        removeMessage(loadingId);
        addMessage('Sorry, something went wrong. Please try again.', 'bot');
    }
}

// Handle button click
async function handleButtonClick(value, displayText) {
    // Show what user selected in chat
    if (displayText) {
        addMessage(displayText, 'user');
    }
    
    // Show loading
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch('/api/button_click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                value: value,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        removeMessage(loadingId);
        
        // Update context
        if (data.context) {
            userContext = { ...userContext, ...data.context };
            updateInfoPanelContext();
        }
        
        // Display response
        displayResponse(data);
        
    } catch (error) {
        console.error('Error:', error);
        removeMessage(loadingId);
        addMessage('Sorry, something went wrong. Please try again.', 'bot');
    }
}

// Update info panel with user context
function updateInfoPanelContext() {
    const panelContent = document.getElementById('panelContent');
    
    let html = '<div class="user-context">';
    html += '<h4>📝 Your Profile</h4>';
    html += '<div class="context-info">';
    
    if (userContext.name) {
        html += `<p><strong>Name:</strong> ${userContext.name}</p>`;
    }
    if (userContext.location || userContext.village) {
        html += `<p><strong>Location:</strong> ${userContext.location || userContext.village}</p>`;
    }
    if (userContext.interests) {
        html += `<p><strong>Interests:</strong> ${userContext.interests}</p>`;
    }
    if (userContext.budget) {
        html += `<p><strong>Budget:</strong> ₹${formatNumber(userContext.budget)}</p>`;
    }
    
    html += '</div>';
    
    // Add quick actions
    html += '<div class="quick-actions">';
    html += '<h4>🚀 Quick Actions</h4>';
    html += '<button class="action-btn" onclick="askQuestion(\'Show me business ideas\')">💡 Get Business Ideas</button>';
    html += '<button class="action-btn" onclick="askQuestion(\'Tell me about government schemes\')">💰 View Schemes</button>';
    html += '<button class="action-btn" onclick="askQuestion(\'Find nearby resources\')">📍 Find Resources</button>';
    html += '<button class="action-btn" onclick="askQuestion(\'I need help\')">❓ Get Help</button>';
    html += '</div>';
    
    html += '</div>';
    
    panelContent.innerHTML = html;
}

// Ask question programmatically
function askQuestion(question) {
    const input = document.getElementById('messageInput');
    input.value = question;
    sendMessage();
}

// Display response based on type
function displayResponse(data) {
    const type = data.type;
    
    // Add text reply
    if (data.reply) {
        addMessage(data.reply, 'bot');
    }
    
    // Add buttons
    if (data.buttons && data.buttons.length > 0) {
        addButtons(data.buttons);
    }
    
    // Display ideas
    if (data.ideas && data.ideas.length > 0) {
        displayIdeas(data.ideas);
        // Also show in chat
        addMessage('I\'ve displayed 5 business ideas in the information panel on the right →', 'bot');
    }
    
    // Display resources
    if (data.resources && data.resources.length > 0) {
        displayResources(data.resources, data.map_center);
        addMessage('I\'ve found nearby resources! Check the information panel →', 'bot');
    }
    
    // Display schemes
    if (data.schemes && data.schemes.length > 0) {
        displaySchemes(data.schemes);
        addMessage('Government schemes are now displayed in the information panel →', 'bot');
    }
    
    // Display plan
    if (data.plan) {
        displayPlan(data.plan);
        addMessage('Your complete startup plan is ready! Check the information panel →', 'bot');
    }
}

// Add message to chat
function addMessage(text, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.id = `msg_${Date.now()}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessage(text);
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv.id;
}

// Format message text
function formatMessage(text) {
    // Convert markdown-like formatting
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

// Add loading message
function addLoadingMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    const loadingId = `loading_${Date.now()}`;
    messageDiv.id = loadingId;
    messageDiv.className = 'message bot-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<div class="loading"></div>';
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return loadingId;
}

// Remove message
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// Add buttons
function addButtons(buttons) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'message-buttons';
    
    buttons.forEach(button => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-primary';
        btn.textContent = button.text;
        btn.onclick = () => handleButtonClick(button.value, button.text);
        buttonsDiv.appendChild(btn);
    });
    
    contentDiv.appendChild(buttonsDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Display ideas - ENHANCED with click functionality
function displayIdeas(ideas) {
    const panelContent = document.getElementById('panelContent');
    
    let html = '<div class="ideas-section">';
    html += '<h3>💡 Your Personalized Business Ideas</h3>';
    html += '<p style="color: #666; margin-bottom: 20px;">Location-aware, budget-realistic ideas with market analysis</p>';
    html += '<div class="ideas-grid">';
    
    ideas.forEach((idea, index) => {
        const ideaId = idea.id || index;
        const title = idea.title || idea.name || 'Business Idea';
        const desc = idea.description || idea.desc || 'No description';
        const minInv = idea.investment_min || idea.required_investment_min || 5000;
        const maxInv = idea.investment_max || idea.required_investment_max || 50000;
        const homeBased = idea.home_based || false;
        const competition = idea.competition_level || 'Unknown';
        const successProb = idea.success_probability || 'Medium';
        const funding = idea.funding_suggestion || '';
        const whyLocation = idea.why_this_location || '';
        
        // Badge colors based on competition
        let compBadgeColor = competition === 'Low' ? '#10b981' : (competition === 'Medium' ? '#f59e0b' : '#ef4444');
        let succBadgeColor = successProb === 'High' ? '#10b981' : (successProb === 'Medium' ? '#f59e0b' : '#ef4444');
        
        // Escape title for HTML attribute
        const escapedTitle = title.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        
        html += `
            <div class="idea-card clickable" onclick="viewIdeaDetails(${ideaId}, '${escapedTitle}')">
                <div class="idea-header">
                    <div class="idea-number">#${index + 1}</div>
                    <div class="idea-badges">
                        ${homeBased ? '<span class="badge badge-home">🏠 Home-Based</span>' : ''}
                        <span class="badge badge-competition" style="background: ${compBadgeColor}">Competition: ${competition}</span>
                        <span class="badge badge-success" style="background: ${succBadgeColor}">Success: ${successProb}</span>
                    </div>
                </div>
                <h4>${title}</h4>
                <p class="idea-desc">${desc.substring(0, 150)}...</p>
                ${whyLocation ? `<p class="why-location">📍 <strong>For Your Location:</strong> ${whyLocation.substring(0, 100)}...</p>` : ''}
                ${funding ? `<p class="funding-hint">💰 <strong>Funding:</strong> ${funding.substring(0, 80)}...</p>` : ''}
                <div class="idea-footer">
                    <p class="investment">� ₹${formatNumber(minInv)} - ₹${formatNumber(maxInv)}</p>
                    <button class="btn-select" onclick="event.stopPropagation(); selectIdeaAndPlan(${ideaId}, '${escapedTitle}')">
                        Select & Plan ➜
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    html += '<button class="action-btn full-width" onclick="askQuestion(\'Show me different business ideas\')">🔄 Show Different Ideas</button>';
    html += '</div>';
    
    panelContent.innerHTML = html;
    
    // Store ideas in context
    userContext.ideas = ideas;
    
    console.log('✅ Ideas displayed with location-aware details');
}

// View idea details
function viewIdeaDetails(ideaId, ideaTitle) {
    console.log(`📋 Viewing details for: ${ideaTitle}`);
    askQuestion(`Tell me complete details about ${ideaTitle} business`);
}

// Select idea and create plan - SIMPLIFIED (select_idea now returns plan)
async function selectIdeaAndPlan(ideaId, ideaTitle) {
    console.log(`✅ Selecting and planning: ${ideaTitle} (ID: ${ideaId})`);
    
    addMessage(`I want to start ${ideaTitle}`, 'user');
    
    const loadingId = addLoadingMessage();
    
    try {
        // select_idea endpoint now returns the plan directly
        const response = await fetch('/api/select_idea', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                idea_id: ideaId,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        console.log('📦 Received data:', data);
        
        removeMessage(loadingId);
        displayResponse(data);
        
    } catch (error) {
        console.error('❌ Error:', error);
        removeMessage(loadingId);
        addMessage('Sorry, something went wrong while creating the plan. Please try again.', 'bot');
    }
}

// Escape HTML for safety
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, "\\'");
}

// Display resources - ENHANCED with click functionality
function displayResources(resources, mapCenter) {
    const panelContent = document.getElementById('panelContent');
    
    let html = '<div class="resources-section">';
    html += '<h3>📍 Nearby Resources</h3>';
    html += '<p style="color: #666; margin-bottom: 15px;">Resources found near your location</p>';
    
    if (mapCenter) {
        html += `<button class="btn btn-primary full-width" onclick="showMap(${mapCenter.lat}, ${mapCenter.lng}, ${JSON.stringify(resources).replace(/"/g, '&quot;')})" style="margin-bottom: 20px;">
            🗺️ View All on Map
        </button>`;
    }
    
    html += '<div class="resources-list">';
    
    // Group resources by type
    const grouped = {};
    resources.forEach(resource => {
        const type = resource.type || 'Other';
        if (!grouped[type]) grouped[type] = [];
        grouped[type].push(resource);
    });
    
    Object.keys(grouped).forEach(type => {
        html += `<div class="resource-group">`;
        html += `<h4 class="resource-type">${type} (${grouped[type].length})</h4>`;
        
        grouped[type].forEach(resource => {
            html += `
                <div class="resource-card clickable" onclick="showResourceDetails('${escapeHtml(resource.name)}', '${escapeHtml(resource.type)}')">
                    <h4>${resource.name}</h4>
                    ${resource.address ? `<p>📍 ${resource.address}</p>` : ''}
                    ${resource.distance_km ? `<p>📏 ${resource.distance_km} km away</p>` : ''}
                    ${resource.phone ? `<p>📞 ${resource.phone}</p>` : ''}
                    ${resource.location ? `<p>📌 ${resource.location}</p>` : ''}
                </div>
            `;
        });
        
        html += '</div>';
    });
    
    html += '</div>';
    html += '<button class="action-btn full-width" onclick="askQuestion(\'Find more resources for my business\')">🔍 Find More Resources</button>';
    html += '</div>';
    
    panelContent.innerHTML = html;
}

// Show resource details
function showResourceDetails(name, type) {
    askQuestion(`Tell me more about ${name} - ${type}`);
}

// Display schemes - ENHANCED with click functionality
function displaySchemes(schemes) {
    const panelContent = document.getElementById('panelContent');
    
    let html = '<div class="schemes-section">';
    html += '<h3>💰 Government Schemes for You</h3>';
    html += '<p style="color: #666; margin-bottom: 20px;">Click on any scheme to learn more about eligibility and application process</p>';
    html += '<div class="schemes-list">';
    
    schemes.forEach((scheme, index) => {
        const title = scheme.title || scheme.name || `Scheme ${index + 1}`;
        const eligibility = scheme.eligibility || 'View details';
        const benefit = scheme.benefit || scheme.benefits || 'Financial assistance';
        
        html += `
            <div class="scheme-card clickable" onclick="viewSchemeDetails('${escapeHtml(title)}')">
                <div class="scheme-header">
                    <h4>${title}</h4>
                    ${scheme.apply_link ? `<span class="status-badge">✓ Apply Online</span>` : ''}
                </div>
                <div class="scheme-body">
                    <p><strong>🎯 Eligibility:</strong> ${eligibility.substring(0, 100)}...</p>
                    <p><strong>💵 Benefit:</strong> ${benefit.substring(0, 100)}...</p>
                    ${scheme.documents ? `<p><strong>📄 Documents:</strong> ${scheme.documents.substring(0, 80)}...</p>` : ''}
                </div>
                <div class="scheme-footer">
                    ${scheme.apply_link ? 
                        `<a href="${scheme.apply_link}" target="_blank" class="apply-link" onclick="event.stopPropagation()">
                            Apply Now →
                        </a>` : 
                        `<button class="btn-link" onclick="event.stopPropagation(); viewSchemeDetails('${escapeHtml(title)}')">
                            View Details →
                        </button>`
                    }
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    html += '<button class="action-btn full-width" onclick="askQuestion(\'How do I apply for these schemes?\')">❓ How to Apply</button>';
    html += '</div>';
    
    panelContent.innerHTML = html;
}

// View scheme details
function viewSchemeDetails(schemeName) {
    askQuestion(`Tell me complete details about ${schemeName} scheme - eligibility, benefits, application process`);
}

// Display plan - ENHANCED with better formatting and click functionality
function displayPlan(plan) {
    const panelContent = document.getElementById('panelContent');
    
    let html = '<div class="plan-section">';
    html += '<h3>📋 Your Complete Startup Plan</h3>';
    html += '<p style="color: #666; margin-bottom: 20px;">Detailed roadmap for your business</p>';
    
    // Overview
    if (plan.overview) {
        html += `<div class="plan-block">
            <h4>🎯 Overview</h4>
            <p>${plan.overview}</p>
        </div>`;
    }
    
    // Investment Breakdown
    if (plan.investment_breakdown) {
        html += '<div class="plan-block"><h4>💰 Investment Breakdown</h4><ul class="investment-list">';
        
        // Handle both array format [{item: "...", cost: 100}] and object format {item: value}
        if (Array.isArray(plan.investment_breakdown)) {
            plan.investment_breakdown.forEach(item => {
                const itemName = item.item || item.description || item.name || 'Item';
                const itemCost = item.cost || item.amount || item.value || 0;
                html += `<li><span class="item-name">${itemName}:</span> <span class="item-value">₹${formatNumber(itemCost)}</span></li>`;
            });
        } else if (typeof plan.investment_breakdown === 'object') {
            Object.entries(plan.investment_breakdown).forEach(([key, value]) => {
                // If value is an object, extract cost/amount
                const cost = typeof value === 'object' ? (value.cost || value.amount || value.value || 0) : value;
                html += `<li><span class="item-name">${key}:</span> <span class="item-value">₹${formatNumber(cost)}</span></li>`;
            });
        }
        html += '</ul></div>';
    }
    
    // Skills Required
    if (plan.skills) {
        html += '<div class="plan-block"><h4>🎓 Skills Required</h4><ul>';
        const skills = Array.isArray(plan.skills) ? plan.skills : [plan.skills];
        skills.forEach(skill => {
            html += `<li>${skill}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Timeline
    if (plan.timeline) {
        html += '<div class="plan-block"><h4>📅 Timeline</h4>';
        
        // Handle both array format [{month: "...", tasks: "..."}] and object format {period: tasks}
        if (Array.isArray(plan.timeline)) {
            plan.timeline.forEach(item => {
                const period = item.month || item.period || item.phase || 'Period';
                const tasks = item.tasks || item.activities || item.description || '';
                html += `<div class="timeline-item">
                    <h5>${period}</h5>
                    <p>${tasks}</p>
                </div>`;
            });
        } else if (typeof plan.timeline === 'object') {
            Object.entries(plan.timeline).forEach(([period, tasks]) => {
                // If tasks is an object, extract the description
                const taskText = typeof tasks === 'object' ? (tasks.tasks || tasks.description || JSON.stringify(tasks)) : tasks;
                html += `<div class="timeline-item">
                    <h5>${period}</h5>
                    <p>${taskText}</p>
                </div>`;
            });
        }
        html += '</div>';
    }
    
    // Resources Needed
    if (plan.resources) {
        html += '<div class="plan-block"><h4>🛠️ Resources Needed</h4><ul>';
        
        // Handle array, object, or string
        if (Array.isArray(plan.resources)) {
            plan.resources.forEach(resource => {
                // If resource is an object, extract the description
                const text = typeof resource === 'object' ? (resource.name || resource.item || resource.description || JSON.stringify(resource)) : resource;
                html += `<li>${text}</li>`;
            });
        } else if (typeof plan.resources === 'object') {
            Object.entries(plan.resources).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${value}</li>`;
            });
        } else {
            html += `<li>${plan.resources}</li>`;
        }
        html += '</ul></div>';
    }
    
    // Target Market
    if (plan.target_market) {
        html += `<div class="plan-block">
            <h4>🎯 Target Market</h4>`;
        
        // Handle object or string
        if (typeof plan.target_market === 'object') {
            html += '<ul>';
            Object.entries(plan.target_market).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${value}</li>`;
            });
            html += '</ul>';
        } else {
            html += `<p>${plan.target_market}</p>`;
        }
        html += '</div>';
    }
    
    // Revenue Estimate
    if (plan.revenue_estimate) {
        html += `<div class="plan-block highlight">
            <h4>💵 Revenue Estimate</h4>`;
        
        // Handle object or string
        if (typeof plan.revenue_estimate === 'object') {
            html += '<ul>';
            Object.entries(plan.revenue_estimate).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${value}</li>`;
            });
            html += '</ul>';
        } else {
            html += `<p>${plan.revenue_estimate}</p>`;
        }
        html += '</div>';
    }
    
    // Risks & Mitigation
    if (plan.risks) {
        html += '<div class="plan-block"><h4>⚠️ Risks & Mitigation</h4><ul>';
        
        // Handle array or string
        if (Array.isArray(plan.risks)) {
            plan.risks.forEach(risk => {
                // If risk is an object with risk/mitigation properties
                if (typeof risk === 'object') {
                    const riskText = risk.risk || risk.problem || risk.issue || '';
                    const mitigation = risk.mitigation || risk.solution || risk.action || '';
                    if (riskText && mitigation) {
                        html += `<li><strong>${riskText}</strong> → ${mitigation}</li>`;
                    } else {
                        html += `<li>${JSON.stringify(risk)}</li>`;
                    }
                } else {
                    html += `<li>${risk}</li>`;
                }
            });
        } else if (typeof plan.risks === 'object') {
            Object.entries(plan.risks).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${value}</li>`;
            });
        } else {
            html += `<li>${plan.risks}</li>`;
        }
        html += '</ul></div>';
    }
    
    // Next Steps
    if (plan.next_steps) {
        html += '<div class="plan-block action-block"><h4>🚀 Next Immediate Steps</h4><ol class="next-steps">';
        const steps = Array.isArray(plan.next_steps) ? plan.next_steps : [plan.next_steps];
        steps.forEach(step => {
            html += `<li>${step}</li>`;
        });
        html += '</ol></div>';
    }
    
    // Full text if available
    if (plan.full_text) {
        html += `<div class="plan-block">
            <h4>📄 Complete Details</h4>
            <div class="full-text">${plan.full_text.replace(/\n/g, '<br>')}</div>
        </div>`;
    }
    
    // Action buttons
    html += '<div class="plan-actions">';
    html += '<button class="action-btn" onclick="askQuestion(\'What are the next steps I should take?\')">🎯 Next Steps</button>';
    html += '<button class="action-btn" onclick="askQuestion(\'How do I get funding for this business?\')">💰 Get Funding</button>';
    html += '<button class="action-btn" onclick="askQuestion(\'Find suppliers and resources for this business\')">📍 Find Resources</button>';
    html += '</div>';
    
    html += '</div>';
    panelContent.innerHTML = html;
}

// Show map
function showMap(lat, lng, resources) {
    const modal = document.getElementById('mapModal');
    modal.style.display = 'block';
    
    // Initialize map
    setTimeout(() => {
        if (currentMap) {
            currentMap.remove();
        }
        
        currentMap = L.map('mapContainer').setView([lat, lng], 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(currentMap);
        
        // Add markers
        if (Array.isArray(resources)) {
            resources.forEach(resource => {
                if (resource.lat && resource.lng) {
                    L.marker([resource.lat, resource.lng])
                        .addTo(currentMap)
                        .bindPopup(`<strong>${resource.name}</strong><br>${resource.type}<br>${resource.address || ''}`);
                }
            });
        }
        
        // Center marker
        L.marker([lat, lng], {
            icon: L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(currentMap).bindPopup('Your Location');
        
    }, 100);
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    if (modalId === 'mapModal' && currentMap) {
        currentMap.remove();
        currentMap = null;
    }
}

// Close modal on outside click
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        if (event.target.id === 'mapModal' && currentMap) {
            currentMap.remove();
            currentMap = null;
        }
    }
}

// Format number with commas
function formatNumber(num) {
    if (!num && num !== 0) return '0';
    // Handle objects by returning the object stringified (shouldn't happen now, but safe)
    if (typeof num === 'object') {
        return JSON.stringify(num);
    }
    // Convert to number if string
    const numValue = typeof num === 'string' ? parseFloat(num.replace(/[^0-9.-]/g, '')) : num;
    if (isNaN(numValue)) return '0';
    return Math.round(numValue).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Startup Sathi loaded!');
    console.log('Session ID:', sessionId);
});
