export default class ChatAPI {
    constructor(apiURL = "/api/v1") {
        this.apiURL = apiURL;
    }

    async fetchNodes() {
        const response = await fetch(this.apiURL + "/llamas");
        return await response.json();
    }

    async switchModel(model_key, node_key) {
        const response = await fetch(this.apiURL + "/switch_model", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_key: model_key,
                node_key: node_key,
            }),
        });
        return await response.json();
    }

    async getPrompts() {
        const response = await fetch(this.apiURL + "/prompts");
        return await response.json();
    }

    async getHistory() {
        const response = await fetch(this.apiURL + "/history");
        return await response.json();
    }


    async postMessage(message, prompt_key) {
        const response = await fetch(this.apiURL + '/infer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                raw_input: message,
                prompt_key: prompt_key
            })
        });
        return await response;
    }

    async submitScore(inference_id, score) {
        const response = await fetch(this.apiURL + '/score', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'Authorization': 'Bearer your-token'  // If needed
            },
            body: JSON.stringify({
                inference_id: inference_id,
                score: score
            })
        })
        return await response.json()
    }

    async submitFeedback(inference_id, feedback) {
        const response = await fetch(this.apiURL + '/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'Authorization': 'Bearer your-token'  // If needed
            },
            body: JSON.stringify({
                inference_id: inference_id,
                feedback: feedback
            })
        })
        return await response.json()
    }

}