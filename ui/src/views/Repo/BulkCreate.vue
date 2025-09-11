<template>
  <v-container>
    <router-view @update:repos="repos = $event"> </router-view>
    <div v-if="repos.length > 0">
      <repository-table :repositories="repos" @update:selected="form.selected = $event">
      </repository-table>
      <p class="text-subtitle-2 mt-6 mb-4">Schedule</p>
      <div class="mb-6">
        <interval-selector v-model="form.interval"></interval-selector>
      </div>
      <v-alert
        v-model="alert.isOpen"
        :text="alert.text"
        :icon="alert.icon"
        :color="alert.color"
        density="compact"
        class="mb-6"
      />
      <v-btn :loading="loading" color="primary" @click="createTasks"> Schedule selected </v-btn>
    </div>
  </v-container>
</template>
<script>
import IntervalSelector from '@/components/IntervalSelector.vue'
import RepositoryTable from '@/components/RepositoryTable.vue'
import { mapState } from 'pinia'
import { useEcosystemStore } from '@/store'
import { API } from '@/services/api'
import { getTaskArgs } from '@/utils/datasources'

export default {
  components: { IntervalSelector, RepositoryTable },
  data() {
    return {
      errorMessage: null,
      loading: false,
      repos: [],
      form: {
        interval: '604800',
        selected: []
      },
      alert: {
        isOpen: false,
        text: '',
        color: 'error',
        icon: 'mdi-warning'
      }
    }
  },
  computed: {
    project() {
      return this.$route?.params?.id
    },
    ...mapState(useEcosystemStore, ['selectedEcosystem'])
  },
  methods: {
    async createTasks() {
      if (this.form.selected.length === 0) return
      this.loading = true

      Promise.allSettled(
        this.form.selected.map((task) => {
          const { datasource_type, category, uri, backend_args } = getTaskArgs(
            task.datasource,
            task.category,
            task.url
          )
          return API.repository.create(this.selectedEcosystem, this.project, {
            datasource_type,
            category,
            uri,
            backend_args,
            scheduler: {
              job_interval: this.form.interval,
              job_max_retries: 3
            }
          })
        })
      )
        .then((responses) => {
          const errors = responses
            .filter((res) => res.status === 'rejected')
            .map((error) => {
              if (error.reason.response.data && typeof error.reason.response.data === 'object') {
                return Object.values(error.reason.response.data).toString()
              } else {
                return error.reason.message
              }
            })
          if (errors.length > 0) {
            Object.assign(this.alert, {
              isOpen: true,
              color: 'error',
              text: errors,
              icon: 'mdi-alert-outline'
            })
          } else {
            this.$router.push({ name: 'tasks' })
          }
        })
        .finally(() => {
          this.loading = false
        })
    }
  }
}
</script>
<style lang="scss" scoped>
:deep(.v-form) {
  max-width: 600px;
}

:deep(.v-table) {
  background-color: transparent;

  .v-table__wrapper {
    background-color: rgb(var(--v-theme-surface));
    border: thin solid rgba(0, 0, 0, 0.08);
    border-radius: 4px;
    max-height: 55vh;
  }
}
</style>
