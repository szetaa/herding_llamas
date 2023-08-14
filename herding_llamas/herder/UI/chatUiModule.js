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
        this.promptsContainer = document.getElementById('promptsContainer');
        this.chatWindow = document.getElementById('chatWindow');
        this.userInput = document.getElementById('userInput');
        this.init();
    }

    async init() {
        //this.populateNodesDropdown();
        this.populatePromptEngineerDropdown();
    }

    async populateNodesDropdown() {
        this.btnStartWorkders = document.getElementById('start_workers')
        this.btnStartWorkders.addEventListener('click', () => {
            this.chatAPI.startWorkers()
        })
        const nodes = await this.chatAPI.fetchNodes();
        this.populateModelCards(nodes);
    }

    async populateModelCards(nodes) {
        this.modelCardContainer.innerHTML = '';
        for (const nodeId in nodes) {
            const node = nodes[nodeId];
            const card = await this.createCard(node, nodeId);
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


    async setupTabs() {
        const allowedTabs = await this.chatAPI.fetchAllowedTabs()

        allowedTabs.forEach(tab => {
            document.getElementById(`tab${tab}`).style.display = 'inline-block'
            document.getElementById(`tab${tab}`).addEventListener('click', () => {
                this.openTab(`view${tab}`)
                tab == 'PromptEngineer' && this.populatePromptEngineerDropdown()
                tab == 'Prompts' && this.populatePrompts()
                tab == 'Nodes' && this.populateNodesDropdown()
                tab == 'History' && this.populateHistory()
                tab == 'OwnHistory' && this.populateHistory()
            })
        })

        document.getElementById('tabPromptEngineer').click();
    }

    async createPromptForm(prompt) {
        const _promptForm = document.getElementById('promptForm')
        _promptForm.innerHTML = ""

        const response = await fetch('./templates/prompt_form.mustache');
        const template = await response.text();

        const preprocessedPrompt = {
            "variables": prompt.variables.map(obj => {
                const key = Object.keys(obj)[0];
                const value = obj[key];
                return { key, value };
            })
        };

        // Render the template with the data
        const rendered = Mustache.render(template, preprocessedPrompt);

        // Create a container element
        _promptForm.innerHTML = rendered;
        this.sendButton = document.getElementById('sendButton');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.listenToMessages();
    }


    async createCard(node, nodeId) {
        // Fetch the template
        const response = await fetch('./templates/model_card.mustache');
        const template = await response.text();

        // Prepare the data for the template
        const data = {
            nodeName: nodeId,
            models: node.models.map(model => ({
                name: model.option,
                selected: model.selected ? 'selected' : ''
            })),
            system_stats: node.system_stats,
            infer_stats: node.infer_stats,
            worker_started: node.worker_started,
        };

        // Render the template with the data
        const rendered = Mustache.render(template, data);

        // Create a container element
        const container = document.createElement('div');
        container.innerHTML = rendered;

        // Add the event listener to the select element
        const select = container.querySelector('select');
        select.addEventListener('change', () => this.chatAPI.switchModel(select.value, nodeId));

        // Return the first child of the container (i.e., the card)
        return container.firstChild;
    }


    async populatePromptEngineerDropdown() {
        const data = await this.chatAPI.getPrompts();
        this.promptSelect.innerHTML = '<option value="">Please select prompt</option>';
        data.prompt_options.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt.prompt;
            option.textContent = prompt.name;
            this.promptSelect.appendChild(option);
        });
        this.promptSelect.addEventListener('change', (prompt) => {
            this.createPromptForm(data.full_prompts[prompt.target.value])
        })
    }

    async populatePrompts() {
        const prompts = await this.chatAPI.getPrompts();

        this.promptsContainer.innerHTML = '';
        const promptsArray = Object.values(prompts.full_prompts);

        // Fetch the template
        fetch('./templates/prompts_table.mustache')
            .then(response => response.text())
            .then(template => {
                // Prepare the data for Mustache
                const view = {
                    prompts: Object.entries(prompts.full_prompts).map(([promptKey, promptValue]) => ({
                        key: promptKey,
                        ...promptValue,
                        variables: promptValue.variables ? promptValue.variables.map(obj => ({ varKey: Object.keys(obj)[0], varVal: Object.values(obj)[0] })) : []
                        ,
                        parameter: promptValue.param
                            ? Object.entries(promptValue.param).map(([key, value]) => `${key}: ${value}`).join('\n')
                            : ''
                    })),
                };
                // Render the template with Mustache
                const rendered = Mustache.render(template, view);

                // Append the rendered HTML to the historyContainer
                this.promptsContainer.innerHTML = rendered;
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
                    headers: ['Info', 'Raw Input', 'Prompt', 'Response', 'Score', 'Feedback'],
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
            // Collecting values from textareas with class "variables"
            const textareas = document.querySelectorAll('textarea.variables');
            let messageData = {};
            textareas.forEach(textarea => {
                messageData[textarea.name] = textarea.value;
            });

            const prompt_key = this.promptSelect.value;
            this.appendHumanMessage(JSON.stringify(messageData)); // Displaying the collected data as a string
            this.loadingSpinner.title = "Waiting for LLM response..";
            this.loadingSpinner.style.display = 'block';

            try {
                const responseData = await this.chatAPI.postMessage(messageData, prompt_key);
                this.loadingSpinner.style.display = 'none';
                this.appendAssistantMessage(responseData['text'], responseData['inference_id']);
            } catch (error) {
                this.loadingSpinner.style.display = 'none';
                this.appendErrorMessage(error.message);
            }
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



}