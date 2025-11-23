/**
 * Example usage of the VideoTrimmer component
 *
 * This file demonstrates how to integrate the VideoTrimmer component
 * into your pages. It can be deleted once you've integrated the component.
 */

"use client"

import { useState } from "react"
import { VideoTrimmer } from "./VideoTrimmer"

export function VideoTrimmerExample() {
  const [trimPoints, setTrimPoints] = useState({ in: 2.5, out: 7.0 })

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Video Trimmer Example</h1>

      <VideoTrimmer
        videoDuration={10.0}
        initialTrimPoints={trimPoints}
        onTrimPointsChange={(newTrimPoints) => {
          setTrimPoints(newTrimPoints)
          console.log("Trim points changed:", newTrimPoints)
        }}
      />

      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-lg font-semibold mb-2">Current State:</h2>
        <pre className="text-sm text-muted-foreground">
          {JSON.stringify(trimPoints, null, 2)}
        </pre>
      </div>
    </div>
  )
}
