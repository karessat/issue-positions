import { useState, useEffect } from 'react'

const PARTY_NAMES = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
}

const PARTY_COLORS = {
  D: 'bg-blue-500',
  R: 'bg-red-500',
  I: 'bg-purple-500',
}

function MemberPanel({ member, onClose }) {
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/members/${member.member_id}`)
      .then(res => res.json())
      .then(data => {
        setDetails(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [member.member_id])

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <div className="flex justify-between items-start">
        <div className="flex gap-4">
          {/* Photo placeholder */}
          <div className={`w-16 h-16 rounded-full ${PARTY_COLORS[member.party]} flex items-center justify-center text-white text-2xl font-bold`}>
            {member.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>

          <div>
            <h3 className="text-xl font-semibold text-gray-900">{member.name}</h3>
            <p className="text-gray-600">
              {PARTY_NAMES[member.party]} - {member.state}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-gray-500">Position Score:</span>
              <span className={`font-mono font-semibold ${
                member.score < 0 ? 'text-blue-600' : member.score > 0 ? 'text-red-600' : 'text-gray-600'
              }`}>
                {member.score > 0 ? '+' : ''}{member.score.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Score visualization */}
      <div className="mt-6">
        <div className="flex justify-between text-sm text-gray-500 mb-1">
          <span>Free Trade</span>
          <span>Protectionist</span>
        </div>
        <div className="h-4 bg-gradient-to-r from-blue-100 via-gray-100 to-red-100 rounded-full relative">
          <div
            className={`absolute w-4 h-4 rounded-full ${PARTY_COLORS[member.party]} border-2 border-white shadow`}
            style={{
              left: `calc(${(member.score + 1) / 2 * 100}% - 8px)`,
              top: 0,
            }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>-1.0</span>
          <span>0</span>
          <span>+1.0</span>
        </div>
      </div>

      {/* Voting Evidence */}
      {loading ? (
        <div className="mt-6 text-gray-500">Loading voting record...</div>
      ) : details?.evidence?.votes?.length > 0 ? (
        <div className="mt-6">
          <h4 className="font-medium text-gray-700 mb-3">Voting Record</h4>
          <div className="space-y-2">
            {details.evidence.votes.map((vote, i) => (
              <div key={i} className="flex items-center gap-3 text-sm p-2 bg-gray-50 rounded">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  vote.vote === 'yes' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {vote.vote.toUpperCase()}
                </span>
                <span className="flex-1 text-gray-700">{vote.bill_title}</span>
                <span className="text-gray-400 text-xs">
                  {vote.bill_position_indicator > 0 ? '+' : ''}{vote.bill_position_indicator?.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Bill indicator shows what a YES vote means on the spectrum (+protectionist, -free trade)
          </p>
        </div>
      ) : (
        <div className="mt-6 text-gray-500 text-sm">No voting evidence available.</div>
      )}
    </div>
  )
}

export default MemberPanel
