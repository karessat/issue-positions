import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const PARTY_COLORS = {
  D: '#3B82F6', // blue
  R: '#EF4444', // red
  I: '#8B5CF6', // purple
}

function SpectrumChart({
  positions,
  leftLabel,
  rightLabel,
  onMemberClick,
  selectedMember,
}) {
  const svgRef = useRef()
  const containerRef = useRef()
  const [tooltip, setTooltip] = useState(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: Math.max(600, width), height: 400 })
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Draw chart
  useEffect(() => {
    if (!positions || !svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const margin = { top: 40, right: 40, bottom: 60, left: 40 }
    const width = dimensions.width - margin.left - margin.right
    const height = dimensions.height - margin.top - margin.bottom

    const g = svg
      .attr('width', dimensions.width)
      .attr('height', dimensions.height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Scale: -1 to 1 maps to 0 to width
    const xScale = d3.scaleLinear().domain([-1, 1]).range([0, width])

    // Add gradient background
    const gradient = svg
      .append('defs')
      .append('linearGradient')
      .attr('id', 'spectrum-gradient')
      .attr('x1', '0%')
      .attr('x2', '100%')

    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#E0F2FE')
    gradient.append('stop').attr('offset', '50%').attr('stop-color', '#F3F4F6')
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#FEE2E2')

    g.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'url(#spectrum-gradient)')
      .attr('rx', 8)

    // Add axis
    const xAxis = d3.axisBottom(xScale).ticks(5).tickFormat(d => d.toFixed(1))

    g.append('g')
      .attr('transform', `translate(0,${height + 10})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#6B7280')

    // Add labels
    g.append('text')
      .attr('x', 0)
      .attr('y', height + 45)
      .attr('text-anchor', 'start')
      .attr('fill', '#374151')
      .attr('font-weight', '600')
      .text(`← ${leftLabel}`)

    g.append('text')
      .attr('x', width)
      .attr('y', height + 45)
      .attr('text-anchor', 'end')
      .attr('fill', '#374151')
      .attr('font-weight', '600')
      .text(`${rightLabel} →`)

    // Center line
    g.append('line')
      .attr('x1', xScale(0))
      .attr('x2', xScale(0))
      .attr('y1', 0)
      .attr('y2', height)
      .attr('stroke', '#9CA3AF')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')

    // Calculate y positions using beeswarm-like layout
    const radius = 8
    const padding = 2

    // Sort by score for consistent layout
    const sortedPositions = [...positions].sort((a, b) => a.score - b.score)

    // Simple collision avoidance
    const positionsWithY = []
    for (const pos of sortedPositions) {
      const x = xScale(pos.score)
      let y = height / 2

      // Find non-overlapping y position
      let attempts = 0
      let direction = 1
      while (attempts < 50) {
        const collision = positionsWithY.some(p => {
          const dx = x - p.x
          const dy = y - p.y
          return Math.sqrt(dx * dx + dy * dy) < (radius + padding) * 2
        })

        if (!collision) break

        // Alternate up and down
        y = height / 2 + direction * (Math.floor(attempts / 2) + 1) * (radius * 2 + padding)
        direction *= -1
        attempts++
      }

      positionsWithY.push({ ...pos, x, y })
    }

    // Draw dots
    const dots = g
      .selectAll('circle.member')
      .data(positionsWithY)
      .enter()
      .append('circle')
      .attr('class', 'member')
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)
      .attr('r', radius)
      .attr('fill', d => PARTY_COLORS[d.party])
      .attr('stroke', d =>
        selectedMember && selectedMember.member_id === d.member_id
          ? '#000'
          : 'white'
      )
      .attr('stroke-width', d =>
        selectedMember && selectedMember.member_id === d.member_id ? 3 : 2
      )
      .attr('cursor', 'pointer')
      .attr('opacity', d =>
        selectedMember
          ? selectedMember.member_id === d.member_id
            ? 1
            : 0.4
          : 0.9
      )
      .on('mouseover', (event, d) => {
        setTooltip({
          x: event.pageX,
          y: event.pageY,
          data: d,
        })
        d3.select(event.target).attr('r', radius + 2)
      })
      .on('mouseout', (event) => {
        setTooltip(null)
        d3.select(event.target).attr('r', radius)
      })
      .on('click', (event, d) => {
        onMemberClick(d)
      })

    // Add title
    svg
      .append('text')
      .attr('x', dimensions.width / 2)
      .attr('y', 24)
      .attr('text-anchor', 'middle')
      .attr('fill', '#111827')
      .attr('font-size', '16px')
      .attr('font-weight', '600')
      .text('Position Spectrum')

  }, [positions, dimensions, selectedMember, leftLabel, rightLabel, onMemberClick])

  return (
    <div ref={containerRef} className="relative">
      <svg ref={svgRef}></svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute bg-gray-900 text-white px-3 py-2 rounded shadow-lg text-sm pointer-events-none z-10"
          style={{
            left: tooltip.x - containerRef.current.getBoundingClientRect().left + 10,
            top: tooltip.y - containerRef.current.getBoundingClientRect().top - 40,
          }}
        >
          <div className="font-semibold">{tooltip.data.name}</div>
          <div className="text-gray-300">
            {tooltip.data.party === 'D' ? 'Democrat' : tooltip.data.party === 'R' ? 'Republican' : 'Independent'}
            {' - '}
            {tooltip.data.state}
          </div>
          <div className="text-gray-300">
            Score: {tooltip.data.score.toFixed(2)}
          </div>
        </div>
      )}
    </div>
  )
}

export default SpectrumChart
