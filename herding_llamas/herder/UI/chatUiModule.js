export default class ChatUI {

    constructor(chatAPI) {
        this.filledStar = '★';  // Replace with actual filled star character or icon
        this.unfilledStar = '☆';  // Replace with actual unfilled star character or icon

        this.chatAPI = chatAPI;
        this.setupTabs();
        this.nodesDropdown = document.getElementById('nodes-dropdown');
        this.modelCardContainer = document.getElementById('model-card-container');
        this.promptSelect = document.getElementById('promptSelect');
        this.historyContainer = document.getElementById('historyContainer');
        this.chatWindow = document.getElementById('chatWindow');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.init();
    }

    async init() {
        this.populateNodesDropdown();
        this.populatePromptsDropdown();
        this.listenToMessages();
    }

    async populateNodesDropdown() {
        const nodes = await this.chatAPI.fetchNodes();
        this.populateModelCards(nodes);
    }

    async populateModelCards(nodes) {
        this.modelCardContainer.innerHTML = '';
        for (const nodeId in nodes) {
            const node = nodes[nodeId];
            const card = this.createCard(node, nodeId);
            this.modelCardContainer.appendChild(card);
        }
    }

    openTab(tab) {
        let tabcontent = document.getElementsByClassName('tabcontent');
        let i = 0
        for (i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = 'none';
        }
        document.getElementById(tab).style.display = 'block';
    }


    setupTabs() {
        document.getElementById('tabNodes').addEventListener('click', () => {
            this.openTab('viewNodes')
            this.populateNodesDropdown();

        })
        document.getElementById('tabPrompts').addEventListener('click', () => {
            this.openTab('viewPrompts')
            this.populatePromptsDropdown();
        })
        document.getElementById('tabHistory').addEventListener('click', () => {
            this.openTab('viewHistory')
            this.populateHistory()
        })
        document.getElementById('tabPrompts').click();
    }


    createCard(node, nodeId) {
        // Create a card for the selected node
        const card = document.createElement('div');
        card.className = 'card';
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        card.appendChild(cardBody);

        // Create a div for the node name
        const nodeName = document.createElement('div');
        nodeName.textContent = nodeId;  // Replace 'node.key' with the property that contains the node name
        nodeName.className = 'node-name';  // Add a class for styling if needed
        cardBody.appendChild(nodeName);

        // Create a dropdown for the models
        const select = document.createElement('select');
        select.className = 'custom-select';
        for (const model of node.models) {
            const option = document.createElement('option');
            option.value = model.option;
            option.textContent = model.option;
            option.selected = model.selected;
            select.appendChild(option);
        }
        cardBody.appendChild(select);
        select.addEventListener('change', () => this.chatAPI.switchModel(select.value, nodeId));
        return card;
    }


    // async switchModel(model_key, node_key) {
    //     const response = await this.chatAPI.switchModel(model_key, node_key);
    //     console.log(response);
    // }

    async populatePromptsDropdown() {
        const data = await this.chatAPI.getPrompts();
        this.promptSelect.innerHTML = ''
        data.prompts.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt.prompt;
            option.textContent = prompt.name;
            this.promptSelect.appendChild(option);
        });
    }

    async populateHistory() {
        const data = await this.chatAPI.getHistory();
        this.historyContainer.innerHTML = '';

        // Fetch the template
        fetch('./templates/feedback_table.mustache')
            .then(response => response.text())
            .then(template => {
                // Prepare the data for Mustache
                const view = {
                    headers: ['Info', 'Raw Input', 'Inferred Input', 'Response', 'Score', 'Feedback'],
                    data: data.map(item => ({
                        ...item,
                        infer_input: item.infer_input, //.replace("<", '&lt;').replace(">", '&gt;'),
                        elapsed_seconds: item.elapsed_seconds.toFixed(1),
                    })),
                };

                // Render the template with Mustache
                const rendered = Mustache.render(template, view);

                // Append the rendered HTML to the historyContainer
                this.historyContainer.innerHTML = rendered;
            });
    }



    listenToMessages() {
        this.sendButton.addEventListener('click', async () => {
            const message = this.userInput.value;
            const prompt_key = this.promptSelect.value;
            this.appendHumanMessage(message);
            this.loadingSpinner.title = "Waiting for LLM response.."
            this.loadingSpinner.style.display = 'block';
            const response = await this.chatAPI.postMessage(message, prompt_key);
            if (response.status === 403) {
                const errorData = await response.json();
                this.loadingSpinner.style.display = 'none';
                this.appendErrorMessage(errorData.detail);
                return;
            }
            if (!response.ok) {
                //const errorData = await response.json();
                this.loadingSpinner.style.display = 'none';
                this.appendErrorMessage("Invalid response");
                return;
            }
            const responseData = await response.json()
            this.loadingSpinner.style.display = 'none';
            this.appendAssistantMessage(responseData['text'], responseData['inference_id']);
            this.clearInput();
        });
    }

    appendErrorMessage(message) {
        const messageElement = document.createElement('p');
        messageElement.classList = "errorMessage";
        messageElement.innerHTML = message;
        this.chatWindow.prepend(messageElement);
    }


    appendHumanMessage(message) {
        const messageElement = document.createElement('p');
        messageElement.classList = "humanMessage";
        messageElement.innerHTML = message;
        this.chatWindow.prepend(messageElement);
    }

    async appendAssistantMessage(message, inference_id) {
        const messageElement = document.createElement('p');
        messageElement.classList = "assistantMessage";
        console.log('INF:', inference_id)
        messageElement.innerHTML = message;

        const starContainer = document.createElement('div');
        starContainer.classList = "starContainer";
        starContainer.dataset.score = '0';  // Store the score value on the star container

        for (let i = 1; i <= 5; i++) {
            const star = document.createElement('a');
            star.textContent = this.unfilledStar;
            star.href = '#';
            star.addEventListener('click', (event) => {
                event.preventDefault();
                this.sendScore(starContainer, inference_id, i);
            });
            starContainer.appendChild(star);
        }

        // Create parent container with a flex layout
        const container = document.createElement('div');
        container.style.display = 'flex';
        container.style.justifyContent = 'space-between';  // Adds some space between the elements

        // Append starContainer to the parent container
        container.appendChild(starContainer);

        // Create Feedback button
        const feedbackButton = document.createElement('button');
        feedbackButton.classList = "btn btn-primary btn-sm";  // Add .btn-sm for a smaller button
        feedbackButton.textContent = "Feedback";
        feedbackButton.dataset.toggle = "modal";
        feedbackButton.dataset.target = `#modal${inference_id}`;

        // Append feedbackButton to the parent container
        container.appendChild(feedbackButton);

        // Append the parent container to the messageElement
        messageElement.appendChild(container);

        // ...

        // Fetch the template
        const response = await fetch('templates/feedback_form.mustache');
        const template = await response.text();

        // Render the template with Mustache
        const rendered = Mustache.render(template, {
            modal_id: `modal${inference_id}`,
            form_id: `form${inference_id}`,
            feedback_id: `feedback${inference_id}`,
        });

        // Create modal
        const modal = document.createElement('div');
        modal.innerHTML = rendered;
        document.body.appendChild(modal);

        // Attach event listener to the form
        document.getElementById(`form${inference_id}`).addEventListener('submit', (event) => {
            console.log('clicked')
            event.preventDefault();
            const feedback = document.getElementById(`feedback${inference_id}`).value;
            this.sendFeedback(inference_id, feedback);
        });


        this.chatWindow.prepend(messageElement);
    }

    sendFeedback(inference_id, feedback) {
        this.chatAPI.submitFeedback(inference_id, feedback).then(() => {
            // Hide the modal after sending the feedback
            const modal = document.getElementById(`modal${inference_id}`);
            modal.classList.remove('show');
            modal.classList.add('hide');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                document.body.removeChild(backdrop);
            }
        });
    }

    sendScore(starContainer, inference_id, score) {
        this.chatAPI.submitScore(inference_id, score).then(() => {
            starContainer.dataset.score = score.toString();
            const stars = starContainer.childNodes;
            for (let i = 0; i < stars.length; i++) {
                stars[i].textContent = i < score ? this.filledStar : this.unfilledStar;
            }
        });
    }



    clearInput() {
        this.userInput.value = '';
    }
}