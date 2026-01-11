import { useState, useEffect } from 'react'
import SpectrumChart from './components/SpectrumChart'
import MemberPanel from './components/MemberPanel'

function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedMember, setSelectedMember] = useState(null)

  useEffect(() => {
    fetch('/api/issues/trade-policy/positions?chamber=senate')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch data')
        return res.json()
      })
      .then(data => {
        setData(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-600">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Where Does the Senate Stand?
          </h1>
          <p className="mt-2 text-gray-600">
            Visualizing the range of positions on policy issues
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Issue Header */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800">
            {data.issue.name}
          </h2>

          {/* Issue Description */}
          {data.issue.description && (
            <p className="mt-3 text-gray-700 leading-relaxed">
              {data.issue.description}
            </p>
          )}

          {/* Spectrum Explanation */}
          {data.issue.spectrum_description && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center gap-4 text-sm">
                <span className="font-medium text-blue-600">{data.issue.spectrum_left_label}</span>
                <span className="flex-1 text-center text-gray-400">← Spectrum →</span>
                <span className="font-medium text-red-600">{data.issue.spectrum_right_label}</span>
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {data.issue.spectrum_description}
              </p>
            </div>
          )}

          {/* Stats */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap gap-6 text-sm">
            <span className="text-gray-500">{data.positions.length} senators positioned</span>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-500"></span>
              <span>Democrats: {data.stats.by_party.D}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              <span>Republicans: {data.stats.by_party.R}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-purple-500"></span>
              <span>Independents: {data.stats.by_party.I}</span>
            </div>
          </div>
        </div>

        {/* Spectrum Visualization */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <SpectrumChart
            positions={data.positions}
            leftLabel={data.issue.spectrum_left_label}
            rightLabel={data.issue.spectrum_right_label}
            onMemberClick={setSelectedMember}
            selectedMember={selectedMember}
          />
        </div>

        {/* Member Detail Panel */}
        {selectedMember && (
          <MemberPanel
            member={selectedMember}
            onClose={() => setSelectedMember(null)}
          />
        )}

        {/* Senators Without Data */}
        {data.no_data && data.no_data.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Insufficient Voting Data ({data.no_data.length})
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              These senators are newly elected or appointed and don't yet have enough
              trade-related votes to calculate a position.
            </p>
            <div className="flex flex-wrap gap-2">
              {data.no_data.map(member => (
                <span
                  key={member.member_id}
                  className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
                    member.party === 'D'
                      ? 'bg-blue-100 text-blue-800'
                      : member.party === 'R'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-purple-100 text-purple-800'
                  }`}
                >
                  {member.name} ({member.state})
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Insights */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            Key Insights
          </h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-700">Intra-Party Diversity</h4>
              <p className="text-sm text-gray-600 mt-1">
                Both parties show significant internal variation on trade policy,
                with scores ranging widely within each party.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-700">Cross-Party Overlap</h4>
              <p className="text-sm text-gray-600 mt-1">
                Some Republicans hold more free-trade positions than some Democrats,
                showing that trade doesn't follow traditional party lines.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-gray-600">
          <p>
            Positions calculated from voting records on trade-related legislation.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
