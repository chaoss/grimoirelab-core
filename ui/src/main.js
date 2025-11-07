import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import sortinghat from 'sortinghat-ui-core'
import 'sortinghat-ui-core/dist/sortinghat-ui.css'
import { base } from './services/api/client'

const pinia = createPinia()
const app = createApp(App)

app.use(router).use(vuetify).use(pinia)

app.use(sortinghat, {
  apiURL: `${base}/api/v1/identities/`,
  router: router
})

app.mount('#app')
