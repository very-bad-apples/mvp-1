/**
 * File-backed storage for project persistence during development.
 * Uses .dev-projects.json for storage with automatic file creation and error handling.
 */

import fs from 'fs/promises'
import path from 'path'
import { Project } from '@/types/project'

/**
 * Get the storage file path from environment variable or use default
 */
const getStorageFilePath = (): string => {
  const filePath = process.env.PROJECTS_STORAGE_FILE || '.dev-projects.json'
  return path.join(process.cwd(), filePath)
}

/**
 * Project storage class with file-backed persistence
 */
class ProjectStore {
  private cache: Map<string, Project> = new Map()
  private initialized = false
  private filePath: string

  constructor() {
    this.filePath = getStorageFilePath()
  }

  /**
   * Initialize the store by loading existing projects from file
   */
  private async initialize(): Promise<void> {
    if (this.initialized) return

    try {
      const data = await fs.readFile(this.filePath, 'utf-8')
      const projects = JSON.parse(data) as Record<string, Project>
      this.cache = new Map(Object.entries(projects))
      console.log(`[ProjectStore] Loaded ${this.cache.size} projects from ${this.filePath}`)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        // File doesn't exist yet, start with empty cache
        console.log(`[ProjectStore] Creating new storage file at ${this.filePath}`)
        await this.save()
      } else {
        console.error('[ProjectStore] Error loading projects:', error)
        throw new Error('Failed to initialize project storage')
      }
    }

    this.initialized = true
  }

  /**
   * Save the cache to disk
   */
  private async save(): Promise<void> {
    try {
      const data = Object.fromEntries(this.cache)
      await fs.writeFile(this.filePath, JSON.stringify(data, null, 2), 'utf-8')
    } catch (error) {
      console.error('[ProjectStore] Error saving projects:', error)
      throw new Error('Failed to save project storage')
    }
  }

  /**
   * Get a project by ID
   */
  async get(projectId: string): Promise<Project | null> {
    await this.initialize()
    return this.cache.get(projectId) || null
  }

  /**
   * Get all projects
   */
  async getAll(): Promise<Project[]> {
    await this.initialize()
    return Array.from(this.cache.values())
  }

  /**
   * Set/create a project
   */
  async set(projectId: string, project: Project): Promise<void> {
    await this.initialize()
    this.cache.set(projectId, project)
    await this.save()
  }

  /**
   * Update an existing project (merges with existing data)
   */
  async update(projectId: string, updates: Partial<Project>): Promise<Project | null> {
    await this.initialize()

    const existing = this.cache.get(projectId)
    if (!existing) {
      return null
    }

    const updated: Project = {
      ...existing,
      ...updates,
      updatedAt: new Date().toISOString(),
    }

    this.cache.set(projectId, updated)
    await this.save()

    return updated
  }

  /**
   * Delete a project
   */
  async delete(projectId: string): Promise<boolean> {
    await this.initialize()

    const existed = this.cache.has(projectId)
    if (existed) {
      this.cache.delete(projectId)
      await this.save()
    }

    return existed
  }

  /**
   * Check if a project exists
   */
  async has(projectId: string): Promise<boolean> {
    await this.initialize()
    return this.cache.has(projectId)
  }

  /**
   * Get projects by status
   */
  async getByStatus(status: Project['status']): Promise<Project[]> {
    await this.initialize()
    return Array.from(this.cache.values()).filter(p => p.status === status)
  }

  /**
   * Clear all projects (use with caution!)
   */
  async clear(): Promise<void> {
    await this.initialize()
    this.cache.clear()
    await this.save()
  }
}

// Export a singleton instance
export const projectStore = new ProjectStore()
