import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode)
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    // Structured client-side error log — the backend has its own
    // request_id-tagged structured logging; this is this tab's equivalent.
    console.error('CivicPulse UI crashed', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ error: null })
  }

  override render() {
    const { error } = this.state
    const { children, fallback } = this.props

    if (error) {
      if (typeof fallback === 'function') {
        return fallback(error, this.handleReset)
      }
      if (fallback) {
        return fallback
      }
      return (
        <div className="panel error-panel" role="alert">
          <h2>Something went wrong in this view</h2>
          <p>{error.message}</p>
          <button type="button" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      )
    }
    return children
  }
}
