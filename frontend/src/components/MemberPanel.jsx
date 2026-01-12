import { useState, useEffect } from 'react'

const PARTY_NAMES = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
}

const PARTY_COLORS = {
  D: 'bg-blue-600',
  R: 'bg-red-600',
  I: 'bg-violet-600',
}

const PARTY_BORDER_COLORS = {
  D: 'border-blue-200',
  R: 'border-red-200',
  I: 'border-violet-200',
}

const PARTY_BG_COLORS = {
  D: 'bg-blue-50',
  R: 'bg-red-50',
  I: 'bg-violet-50',
}

function MemberPanel({ member, onClose }) {
  const [details, setDetails] = useState(null)
  const [statements, setStatements] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statementsLoading, setStatementsLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/members/${member.member_id}`)
      .then(res => res.json())
      .then(data => {
        setDetails(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))

    // Fetch statements
    setStatementsLoading(true)
    fetch(`/api/members/${member.member_id}/statements`)
      .then(res => res.json())
      .then(data => {
        setStatements(data)
        setStatementsLoading(false)
      })
      .catch(() => setStatementsLoading(false))
  }, [member.member_id])

  return (
    <div className={`bg-white rounded-xl shadow-sm border ${PARTY_BORDER_COLORS[member.party]} p-6 mb-8`}>
      <div className="flex justify-between items-start">
        <div className="flex gap-5">
          {/* Photo placeholder */}
          <div className={`w-20 h-20 rounded-full ${PARTY_COLORS[member.party]} flex items-center justify-center text-white text-2xl font-bold shadow-md`}>
            {member.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>

          <div>
            <h3 className="text-2xl font-bold text-gray-900">{member.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2.5 h-2.5 rounded-full ${PARTY_COLORS[member.party]}`}></span>
              <span className="text-gray-600 font-medium">
                {PARTY_NAMES[member.party]}
              </span>
              <span className="text-gray-400">·</span>
              <span className="text-gray-600">{member.state}</span>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <span className="text-sm text-gray-500">Position Score:</span>
              <span className={`font-mono text-lg font-bold px-2 py-0.5 rounded ${
                member.score < -0.2 ? 'text-blue-700 bg-blue-50' :
                member.score > 0.2 ? 'text-red-700 bg-red-50' :
                'text-gray-700 bg-gray-100'
              }`}>
                {member.score > 0 ? '+' : ''}{member.score.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded-lg"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Score visualization */}
      <div className="mt-8 p-4 bg-gray-50 rounded-xl">
        <div className="flex justify-between text-sm font-medium mb-2">
          <span className="text-blue-600">Free Trade</span>
          <span className="text-gray-400 text-xs">← Position on Spectrum →</span>
          <span className="text-red-600">Protectionist</span>
        </div>
        <div className="h-5 bg-gradient-to-r from-blue-200 via-gray-200 to-red-200 rounded-full relative shadow-inner">
          <div
            className={`absolute w-5 h-5 rounded-full ${PARTY_COLORS[member.party]} border-2 border-white shadow-md transition-all`}
            style={{
              left: `calc(${(member.score + 1) / 2 * 100}% - 10px)`,
              top: 0,
            }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-2 font-mono">
          <span>-1.0</span>
          <span>0</span>
          <span>+1.0</span>
        </div>
      </div>

      {/* Voting Evidence */}
      {loading ? (
        <div className="mt-8 flex items-center gap-2 text-gray-500">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading voting record...
        </div>
      ) : details?.evidence?.votes?.length > 0 ? (
        <div className="mt-8">
          <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Voting Record
          </h4>
          <div className="space-y-2">
            {details.evidence.votes.map((vote, i) => (
              <div key={i} className="flex items-center gap-3 text-sm p-3 bg-gray-50 rounded-lg border border-gray-100 hover:bg-gray-100 transition-colors">
                <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                  vote.vote === 'yes'
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-red-100 text-red-700 border border-red-200'
                }`}>
                  {vote.vote.toUpperCase()}
                </span>
                <span className="flex-1 text-gray-700 font-medium">{vote.bill_title}</span>
                <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                  vote.bill_position_indicator > 0 ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'
                }`}>
                  {vote.bill_position_indicator > 0 ? '+' : ''}{vote.bill_position_indicator?.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-gray-500 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Bill indicator shows what a YES vote means: positive (+) is more protectionist, negative (-) is more free trade
          </p>
        </div>
      ) : (
        <div className="mt-8 text-gray-500 text-sm p-4 bg-gray-50 rounded-lg text-center">
          No voting evidence available for this senator.
        </div>
      )}

      {/* Statements Section */}
      {statementsLoading ? (
        <div className="mt-8 flex items-center gap-2 text-gray-500">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading statements...
        </div>
      ) : statements?.statements?.length > 0 ? (
        <div className="mt-8">
          <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Floor Statements
            <span className="text-xs font-normal text-gray-500">({statements.statements.length})</span>
          </h4>
          <div className="space-y-4">
            {statements.statements.map((stmt) => (
              <div key={stmt.id} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                {stmt.title && (
                  <div className="font-medium text-gray-800 mb-2">{stmt.title}</div>
                )}
                <p className="text-sm text-gray-600 leading-relaxed">
                  "{stmt.text.length > 300 ? stmt.text.slice(0, 300) + '...' : stmt.text}"
                </p>
                <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {new Date(stmt.source_date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                  {stmt.cr_page && (
                    <span className="text-gray-400">
                      Congressional Record p. {stmt.cr_page}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-8 text-gray-500 text-sm p-4 bg-gray-50 rounded-lg text-center">
          No floor statements on trade policy found for this senator.
        </div>
      )}
    </div>
  )
}

export default MemberPanel
