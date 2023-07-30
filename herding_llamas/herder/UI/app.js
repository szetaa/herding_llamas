import ChatAPI from './chatApiModule.js';
import ChatUI from './chatUiModule.js';

window.onload = () => {

    const chatAPI = new ChatAPI();
    new ChatUI(chatAPI);
};
