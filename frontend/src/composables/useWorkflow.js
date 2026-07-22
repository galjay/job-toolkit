import { computed, ref } from 'vue'


export function useWorkflow() {
  const analysis = ref(null)
  const resume = ref(null)
  const decisions = ref({})

  function setAnalysis(value) {
    analysis.value = value
    resume.value = structuredClone(value.resume)
    decisions.value = {}
  }

  function acceptSuggestion(suggestion, editedText) {
    if (!resume.value) return
    resume.value = replaceResumeText(
      resume.value,
      suggestion.original,
      editedText || suggestion.optimized,
    )
    decisions.value[suggestion.id] = 'accepted'
  }

  function rejectSuggestion(suggestion) {
    decisions.value[suggestion.id] = 'rejected'
  }

  const unresolvedCount = computed(() => {
    if (!analysis.value) return 0
    return analysis.value.suggestions.filter(
      (item) => item.requires_user_input && !decisions.value[item.id],
    ).length
  })

  return {
    analysis,
    resume,
    decisions,
    unresolvedCount,
    setAnalysis,
    acceptSuggestion,
    rejectSuggestion,
  }
}


function replaceResumeText(value, original, replacement) {
  if (typeof value === 'string') {
    return value.includes(original) ? value.replace(original, replacement) : value
  }
  if (Array.isArray(value)) {
    return value.map((item) => replaceResumeText(item, original, replacement))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        replaceResumeText(item, original, replacement),
      ]),
    )
  }
  return value
}
