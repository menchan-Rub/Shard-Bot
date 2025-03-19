import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import crypto from 'crypto'

// APIサーバーのベースURL
const API_ENDPOINT = process.env.API_ENDPOINT || 'http://localhost:8000'
const DISCORD_CLIENT_ID = process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID
const REDIRECT_URI = process.env.NEXT_PUBLIC_DISCORD_REDIRECT_URI || 'http://localhost:3000/auth/callback'

export async function GET(request: NextRequest) {
  try {
    // CSRF対策のためのstateパラメータを生成
    const state = crypto.randomBytes(16).toString('hex')
    
    // Cookieにstateを保存
    cookies().set('discord_oauth_state', state, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 10, // 10分間有効
      path: '/',
      sameSite: 'lax'
    })

    // Discord OAuthのURLを構築
    const authUrl = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=identify%20guilds&state=${state}`

    // バックエンドからURLを取得する場合
    try {
      const response = await fetch(`${API_ENDPOINT}/auth/discord/url`)
      if (response.ok) {
        const data = await response.json()
        // URLにstateパラメータを追加
        const url = new URL(data.url)
        url.searchParams.set('state', state)
        
        return NextResponse.json({ url: url.toString() })
      }
    } catch (error) {
      console.warn('APIサーバーからの認証URL取得に失敗:', error)
      // APIサーバーから取得できない場合はフロントエンドで生成したURLを使用
    }

    return NextResponse.json({ url: authUrl })
  } catch (error) {
    console.error('認証URL生成エラー:', error)
    return NextResponse.json(
      { error: '認証URLの生成に失敗しました' },
      { status: 500 }
    )
  }
} 