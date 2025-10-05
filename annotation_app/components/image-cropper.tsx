"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Crop, RotateCcw } from "lucide-react"

interface ImageCropperProps {
  imageUrl: string
  onCropComplete: (croppedImage: string, bbox: any) => void
}

export default function ImageCropper({ imageUrl, onCropComplete }: ImageCropperProps) {
  const [isSelecting, setIsSelecting] = useState(false)
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null)
  const [endPoint, setEndPoint] = useState<{ x: number; y: number } | null>(null)
  const [selection, setSelection] = useState<{
    x: number
    y: number
    width: number
    height: number
  } | null>(null)

  const imageRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!imageRef.current) return

    const rect = imageRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    setStartPoint({ x, y })
    setIsSelecting(true)
    setSelection(null)
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isSelecting || !startPoint || !imageRef.current) return

    const rect = imageRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    setEndPoint({ x, y })
  }

  const handleMouseUp = () => {
    if (!startPoint || !endPoint || !imageRef.current) return

    const x = Math.min(startPoint.x, endPoint.x)
    const y = Math.min(startPoint.y, endPoint.y)
    const width = Math.abs(endPoint.x - startPoint.x)
    const height = Math.abs(endPoint.y - startPoint.y)

    if (width > 10 && height > 10) {
      setSelection({ x, y, width, height })
    }

    setIsSelecting(false)
    setStartPoint(null)
    setEndPoint(null)
  }

  const cropImage = useCallback(() => {
    if (!selection || !imageRef.current || !canvasRef.current) return

    const image = imageRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")

    if (!ctx) return

    // Calculate scale factors
    const scaleX = image.naturalWidth / image.offsetWidth
    const scaleY = image.naturalHeight / image.offsetHeight

    // Set canvas size to match crop area
    canvas.width = selection.width * scaleX
    canvas.height = selection.height * scaleY

    // Draw cropped image
    ctx.drawImage(
      image,
      selection.x * scaleX,
      selection.y * scaleY,
      selection.width * scaleX,
      selection.height * scaleY,
      0,
      0,
      canvas.width,
      canvas.height,
    )

    // Convert to base64
    const croppedImage = canvas.toDataURL("image/png")

    // Calculate relative bounding box
    const bbox = {
      x: (selection.x * scaleX) / image.naturalWidth,
      y: (selection.y * scaleY) / image.naturalHeight,
      width: (selection.width * scaleX) / image.naturalWidth,
      height: (selection.height * scaleY) / image.naturalHeight,
    }

    onCropComplete(croppedImage, bbox)
  }, [selection, onCropComplete])

  const resetSelection = () => {
    setSelection(null)
    setStartPoint(null)
    setEndPoint(null)
    setIsSelecting(false)
  }

  const getCurrentSelection = () => {
    if (selection) return selection
    if (isSelecting && startPoint && endPoint) {
      return {
        x: Math.min(startPoint.x, endPoint.x),
        y: Math.min(startPoint.y, endPoint.y),
        width: Math.abs(endPoint.x - startPoint.x),
        height: Math.abs(endPoint.y - startPoint.y),
      }
    }
    return null
  }

  const currentSelection = getCurrentSelection()

  return (
    <Card>
      <CardContent className="p-4">
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Click and drag to select the inconsistency area in the image
          </div>

          <div className="relative inline-block">
            <img
              ref={imageRef}
              src={imageUrl || "/placeholder.svg"}
              alt="PDF Page"
              className="max-w-full h-auto border cursor-crosshair max-h-[50vh] object-contain"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              draggable={false}
            />

            {currentSelection && (
              <div
                className="absolute border-2 border-blue-500 bg-blue-500 bg-opacity-20 pointer-events-none"
                style={{
                  left: currentSelection.x,
                  top: currentSelection.y,
                  width: currentSelection.width,
                  height: currentSelection.height,
                }}
              />
            )}
          </div>

          <div className="flex gap-2">
            <Button onClick={cropImage} disabled={!selection} className="flex items-center gap-2">
              <Crop className="w-4 h-4" />
              Crop Selection
            </Button>

            <Button onClick={resetSelection} variant="outline" className="flex items-center gap-2">
              <RotateCcw className="w-4 h-4" />
              Reset
            </Button>
          </div>

          <canvas ref={canvasRef} className="hidden" />
        </div>
      </CardContent>
    </Card>
  )
}
