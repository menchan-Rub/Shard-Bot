import { NextRequest, NextResponse } from 'next/server'

// APIサーバーのベースURL
const API_ENDPOINT = process.env.API_ENDPOINT || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const code = searchParams.get('code')

    if (!code) {
      return NextResponse.json(
        { 
          error: '認証コードが見つかりません' 
        }, 
        { status: 400 }
      )
    }

    // CSRF保護
    const state = searchParams.get('state')
    const storedState = request.cookies.get('discord_oauth_state')?.value

    if (process.env.NODE_ENV === 'production' && (!state || !storedState || state !== storedState)) {
      return NextResponse.json(
        { 
          error: '不正なリクエストです' 
        }, 
        { status: 403 }
      )
    }

    // ログインリクエストをAPIサーバーに転送
    const formData = new FormData()
    formData.append('code', code)

    const response = await fetch(`${API_ENDPOINT}/auth/discord/callback`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(10000) // 10秒のタイムアウト
    })

    if (!response.ok) {
      // エラーオブジェクトを解析
      const errorData = await response.json()
      return NextResponse.json(
        { 
          error: '認証に失敗しました', 
          detail: errorData.detail || '不明なエラーが発生しました'
        }, 
        { status: response.status }
      )
    }

    const data = await response.json()

    // センシティブな情報を削除
    if (data.user) {
      data.user = {
        id: data.user.id,
        username: data.user.username,
        discord_id: data.user.discord_id,
        avatar: data.user.avatar
      }
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Discord認証エラー:', error)
    
    return NextResponse.json(
      { 
        error: '認証処理中にエラーが発生しました',
        detail: process.env.NODE_ENV === 'development' 
          ? error instanceof Error ? error.message : '不明なエラー' 
          : undefined
      }, 
      { status: 500 }
    )
  }
} 