import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ImageWithFallback } from '../figma/ImageWithFallback'

describe('ImageWithFallback', () => {
  it('renders the provided src', () => {
    render(<ImageWithFallback src="/foo.png" alt="Foo" data-testid="img" />)
    const img = screen.getByTestId('img') as HTMLImageElement
    expect(img.tagName).toBe('IMG')
    expect(img.src).toContain('/foo.png')
    expect(img.alt).toBe('Foo')
  })

  it('swaps to fallback on error', () => {
    render(<ImageWithFallback src="/broken.png" alt="Broken" data-testid="img" />)
    const img = screen.getByTestId('img') as HTMLImageElement

    fireEvent.error(img)

    const fallbackImg = screen.getByAltText('Error loading image') as HTMLImageElement
    expect(fallbackImg).toBeInTheDocument()
    expect(fallbackImg.src).toContain('data:image/svg+xml;base64')
  })

  it('passes className and style through', () => {
    render(<ImageWithFallback src="/bar.png" alt="Bar" className="my-class" style={{ width: 100 }} data-testid="img" />)
    const img = screen.getByTestId('img')
    expect(img).toHaveClass('my-class')
  })
})
