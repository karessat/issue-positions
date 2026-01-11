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
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
            Where Does the Senate Stand?
          </h1>
          <p className="mt-3 text-lg text-gray-600">
            Visualizing the range of positions on policy issues
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Issue Header */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900">
            {data.issue.name}
          </h2>

          {/* Issue Description */}
          {data.issue.description && (
            <p className="mt-4 text-gray-700 leading-relaxed text-lg">
              {data.issue.description}
            </p>
          )}

          {/* Spectrum Explanation */}
          {data.issue.spectrum_description && (
            <div className="mt-6 p-5 bg-gradient-to-r from-blue-50 via-gray-50 to-red-50 rounded-xl border border-gray-200">
              <div className="flex items-center justify-between text-sm font-semibold">
                <span className="text-blue-600 flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-blue-600"></span>
                  {data.issue.spectrum_left_label}
                </span>
                <span className="text-gray-400 text-xs uppercase tracking-wide">Spectrum</span>
                <span className="text-red-600 flex items-center gap-1">
                  {data.issue.spectrum_right_label}
                  <span className="w-3 h-3 rounded-full bg-red-600"></span>
                </span>
              </div>
              <p className="mt-3 text-sm text-gray-600 text-center">
                {data.issue.spectrum_description}
              </p>
            </div>
          )}

          {/* Stats */}
          <div className="mt-6 pt-5 border-t border-gray-100 flex flex-wrap items-center gap-6 text-sm">
            <span className="text-gray-600 font-medium">{data.positions.length} senators positioned</span>
            <div className="flex items-center gap-5 ml-auto">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-600"></span>
                <span className="text-gray-700">Democrats: <span className="font-semibold">{data.stats.by_party.D}</span></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-600"></span>
                <span className="text-gray-700">Republicans: <span className="font-semibold">{data.stats.by_party.R}</span></span>
              </div>
              {data.stats.by_party.I > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-violet-600"></span>
                  <span className="text-gray-700">Independents: <span className="font-semibold">{data.stats.by_party.I}</span></span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Spectrum Visualization */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <SpectrumChart
            positions={data.positions}
            leftLabel={data.issue.spectrum_left_label}
            rightLabel={data.issue.spectrum_right_label}
            onMemberClick={setSelectedMember}
            selectedMember={selectedMember}
          />
          <p className="text-center text-sm text-gray-500 mt-4">
            Click on any dot to see details about that senator's position
          </p>
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
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Insufficient Voting Data
              <span className="ml-2 text-sm font-normal text-gray-500">({data.no_data.length} senators)</span>
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              These senators are newly elected or appointed and don't yet have enough
              trade-related votes to calculate a position.
            </p>
            <div className="flex flex-wrap gap-2">
              {data.no_data.map(member => (
                <span
                  key={member.member_id}
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                    member.party === 'D'
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : member.party === 'R'
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : 'bg-violet-50 text-violet-700 border border-violet-200'
                  }`}
                >
                  {member.name} ({member.state})
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Insights */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-5">
            Key Insights
          </h3>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800">Intra-Party Diversity</h4>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                  Both parties show significant internal variation on trade policy,
                  with scores ranging widely within each party.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-violet-100 to-gray-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800">Cross-Party Overlap</h4>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                  Some Republicans hold more free-trade positions than some Democrats,
                  showing that trade doesn't follow traditional party lines.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-8 text-center">
          <p className="text-sm text-gray-600">
            Positions calculated from voting records on trade-related legislation.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Data sources: Congress.gov voting records
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
