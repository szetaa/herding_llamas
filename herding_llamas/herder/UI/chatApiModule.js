export default class ChatAPI {
    constructor(apiURL = "/api/v1") {
        this.apiURL = apiURL;
    }

    get_or_set_token() {
        let token = document.cookie.replace(/(?:(?:^|.*;\s*)token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
        if (!token) {
            // If there's no token in the cookies, ask the user for it
            token = prompt("Please enter your token:");
            document.cookie = `token=${token}; Secure;`;
        }
        return token;
    }

    async fetchAllowedTabs() {
        let token = this.get_or_set_token();
        const response = await fetch('/api/v1/allowed_tabs', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            }
        });
        const allowedTabs = await response.json();
        return allowedTabs
    }

    async fetchNodes() {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + "/llamas", {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            }
        });
        return await response.json();
    }

    async switchModel(model_key, node_key) {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + "/switch_model", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                model_key: model_key,
                node_key: node_key,
            }),
        });
        return await response.json();
    }

    async getPrompts() {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + "/prompts", {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            }
        });
        return await response.json();
    }

    async getHistory() {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + "/history", {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            }
        });
        return await response.json();
    }


    async postMessage(message, prompt_key) {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + '/infer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                raw_input: message,
                prompt_key: prompt_key
            })
        });
        const responseBody = await response.json();
        if (!response.ok) {
            // Throw an error with the error message from the server
            throw new Error(responseBody.detail);
        }
        // Return the parsed response body
        return responseBody;
    }

    async submitScore(inference_id, score) {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + '/score', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                inference_id: inference_id,
                score: score
            })
        })
        return await response.json()
    }

    async submitFeedback(inference_id, feedback) {
        let token = this.get_or_set_token();
        const response = await fetch(this.apiURL + '/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                inference_id: inference_id,
                feedback: feedback
            })
        })
        return await response.json()
    }

}