import Terminal from "@/components/Terminal";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">
            🤖 Virtual Lenny
          </h1>
          <p className="text-gray-400 text-lg">
            RAG-Powered Product Management Assistant
          </p>
          <div className="mt-4 flex gap-2 justify-center text-sm text-gray-500 flex-wrap">
            <span className="px-3 py-1 bg-gray-800 rounded-full">
              AWS Lambda
            </span>
            <span className="px-3 py-1 bg-gray-800 rounded-full">
              Bedrock Nova
            </span>
            <span className="px-3 py-1 bg-gray-800 rounded-full">
              Qdrant Cloud
            </span>
            <span className="px-3 py-1 bg-gray-800 rounded-full">
              WebSocket API
            </span>
            <span className="px-3 py-1 bg-gray-800 rounded-full">
              Step Functions
            </span>
          </div>
        </div>

        {/* Terminal */}
        <Terminal />

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>
            Built with Next.js 15 • Deployed on Vercel • Powered by AWS
          </p>
          <p className="mt-2 text-xs text-gray-600">
            MLOps Assignment - Virtual Lenny RAG System
          </p>
        </div>
      </div>
    </main>
  );
}