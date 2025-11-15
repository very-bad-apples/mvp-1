export default function TestEnv() {
  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">Environment Variables Test</h1>
      <div className="space-y-2">
        <p><strong>API URL:</strong> {process.env.NEXT_PUBLIC_API_URL || 'Not set'}</p>
        <p><strong>WS URL:</strong> {process.env.NEXT_PUBLIC_WS_URL || 'Not set'}</p>
        <p><strong>App Name:</strong> {process.env.NEXT_PUBLIC_APP_NAME || 'Not set'}</p>
      </div>
    </div>
  )
}
