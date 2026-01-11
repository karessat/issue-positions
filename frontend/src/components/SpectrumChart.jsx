import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const PARTY_COLORS = {
  D: '#2563EB', // blue-600
  R: '#DC2626', // red-600
  I: '#7C3AED', // violet-600
}

const PARTY_COLORS_LIGHT = {
  D: '#DBEAFE', // blue-100
  R: '#FEE2E2', // red-100
  I: '#EDE9FE', // violet-100
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
  const [containerWidth, setContainerWidth] = useState(800)

  // Handle resize - only track width, height is calculated from data
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect()
        setContainerWidth(Math.max(600, width))
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

    const margin = { top: 20, right: 50, bottom: 70, left: 50 }
    const width = containerWidth - margin.left - margin.right

    // Calculate positions first to determine needed height
    const radius = 12
    const padding = 1
    const xScale = d3.scaleLinear().domain([-1, 1]).range([0, width])

    // Shuffle positions so R and D dots intermix when stacking
    const shuffledPositions = [...positions].sort(() => Math.random() - 0.5)

    // Calculate Y positions with collision avoidance (using 0 as center)
    const positionsWithY = []
    for (const pos of shuffledPositions) {
      const x = xScale(pos.score)
      let y = 0  // Start at center (will adjust later)

      let attempts = 0
      let direction = 1
      while (attempts < 50) {
        const collision = positionsWithY.some(p => {
          const dx = x - p.x
          const dy = y - p.y
          return Math.sqrt(dx * dx + dy * dy) < (radius + padding) * 2
        })

        if (!collision) break

        y = direction * (Math.floor(attempts / 2) + 1) * (radius * 2 + padding)
        direction *= -1
        attempts++
      }

      positionsWithY.push({ ...pos, x, y })
    }

    // Find the extent of Y positions
    const yExtent = d3.extent(positionsWithY, d => d.y)
    const yMin = yExtent[0] - radius - padding
    const yMax = yExtent[1] + radius + padding
    const contentHeight = yMax - yMin

    // Dynamic height based on content
    const height = Math.max(200, contentHeight + 40)  // Add some extra padding

    // Shift all Y positions so they're centered in the chart
    const yOffset = height / 2
    positionsWithY.forEach(p => { p.y += yOffset })

    // Add drop shadow filter
    const defs = svg.append('defs')

    const filter = defs.append('filter')
      .attr('id', 'drop-shadow')
      .attr('height', '130%')
    filter.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 1)
      .attr('stdDeviation', 2)
      .attr('flood-opacity', 0.15)

    const totalHeight = height + margin.top + margin.bottom
    const g = svg
      .attr('width', containerWidth)
      .attr('height', totalHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Add gradient background
    const gradient = defs
      .append('linearGradient')
      .attr('id', 'spectrum-gradient')
      .attr('x1', '0%')
      .attr('x2', '100%')

    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#DBEAFE')
    gradient.append('stop').attr('offset', '50%').attr('stop-color', '#F9FAFB')
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#FEE2E2')

    // Background rectangle
    g.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'url(#spectrum-gradient)')
      .attr('rx', 12)
      .attr('stroke', '#E5E7EB')
      .attr('stroke-width', 1)

    // Grid lines
    const gridLines = [-0.5, 0, 0.5]
    gridLines.forEach(val => {
      g.append('line')
        .attr('x1', xScale(val))
        .attr('x2', xScale(val))
        .attr('y1', 0)
        .attr('y2', height)
        .attr('stroke', val === 0 ? '#9CA3AF' : '#D1D5DB')
        .attr('stroke-width', val === 0 ? 1.5 : 1)
        .attr('stroke-dasharray', val === 0 ? '6,4' : '3,3')
    })

    // Add axis with custom styling
    const xAxis = d3.axisBottom(xScale)
      .ticks(5)
      .tickFormat(d => d.toFixed(1))
      .tickSize(0)

    const axisGroup = g.append('g')
      .attr('transform', `translate(0,${height + 15})`)
      .call(xAxis)

    axisGroup.select('.domain').remove()
    axisGroup.selectAll('text')
      .attr('fill', '#6B7280')
      .attr('font-size', '12px')

    // Add labels with better styling
    g.append('text')
      .attr('x', 0)
      .attr('y', height + 50)
      .attr('text-anchor', 'start')
      .attr('fill', '#2563EB')
      .attr('font-weight', '600')
      .attr('font-size', '14px')
      .text(`← ${leftLabel}`)

    g.append('text')
      .attr('x', width)
      .attr('y', height + 50)
      .attr('text-anchor', 'end')
      .attr('fill', '#DC2626')
      .attr('font-weight', '600')
      .attr('font-size', '14px')
      .text(`${rightLabel} →`)

    // Center label
    g.append('text')
      .attr('x', xScale(0))
      .attr('y', height + 50)
      .attr('text-anchor', 'middle')
      .attr('fill', '#6B7280')
      .attr('font-size', '12px')
      .text('Mixed')

    // Draw dots with party letters for accessibility
    const memberGroups = g.selectAll('g.member')
      .data(positionsWithY)
      .enter()
      .append('g')
      .attr('class', 'member')
      .attr('transform', d => `translate(${d.x},${d.y})`)
      .attr('cursor', 'pointer')
      .attr('opacity', d =>
        selectedMember
          ? selectedMember.member_id === d.member_id
            ? 1
            : 0.35
          : 1
      )
      .style('transition', 'opacity 0.15s ease')
      .on('mouseover', function(event, d) {
        setTooltip({
          x: event.pageX,
          y: event.pageY,
          data: d,
        })
        d3.select(this).select('circle')
          .attr('r', radius + 3)
          .attr('stroke-width', 3)
      })
      .on('mouseout', function(event, d) {
        setTooltip(null)
        d3.select(this).select('circle')
          .attr('r', radius)
          .attr('stroke-width',
            selectedMember && selectedMember.member_id === d.member_id ? 3 : 2
          )
      })
      .on('click', (event, d) => {
        onMemberClick(d)
      })

    // Add circles to groups
    memberGroups.append('circle')
      .attr('r', radius)
      .attr('fill', d => PARTY_COLORS[d.party])
      .attr('stroke', d =>
        selectedMember && selectedMember.member_id === d.member_id
          ? '#1F2937'
          : 'white'
      )
      .attr('stroke-width', d =>
        selectedMember && selectedMember.member_id === d.member_id ? 3 : 2
      )
      .attr('filter', 'url(#drop-shadow)')
      .style('transition', 'all 0.15s ease')

    // Add party letter text to groups
    memberGroups.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', 'white')
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .attr('pointer-events', 'none')
      .text(d => d.party)

  }, [positions, containerWidth, selectedMember, leftLabel, rightLabel, onMemberClick])

  return (
    <div ref={containerRef} className="relative">
      <svg ref={svgRef}></svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute bg-white text-gray-900 px-4 py-3 rounded-lg shadow-xl text-sm pointer-events-none z-10 border border-gray-200"
          style={{
            left: Math.min(
              tooltip.x - containerRef.current.getBoundingClientRect().left + 12,
              containerWidth - 200
            ),
            top: tooltip.y - containerRef.current.getBoundingClientRect().top - 80,
          }}
        >
          <div className="font-semibold text-base">{tooltip.data.name}</div>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                tooltip.data.party === 'D' ? 'bg-blue-600' :
                tooltip.data.party === 'R' ? 'bg-red-600' : 'bg-violet-600'
              }`}
            />
            <span className="text-gray-600">
              {tooltip.data.party === 'D' ? 'Democrat' : tooltip.data.party === 'R' ? 'Republican' : 'Independent'}
              {' · '}
              {tooltip.data.state}
            </span>
          </div>
          <div className="mt-2 pt-2 border-t border-gray-100">
            <span className="text-gray-500">Position: </span>
            <span className={`font-mono font-semibold ${
              tooltip.data.score < -0.2 ? 'text-blue-600' :
              tooltip.data.score > 0.2 ? 'text-red-600' : 'text-gray-600'
            }`}>
              {tooltip.data.score > 0 ? '+' : ''}{tooltip.data.score.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default SpectrumChart
