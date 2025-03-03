import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const token = request.headers.get('authorization')?.replace('Bearer ', '')
    
    if (!token) {
      return NextResponse.json(
        { error: '認証トークンがありません' },
        { status: 401 }
      )
    }

    console.log('セッション検証リクエスト送信:', {
      url: 'http://localhost:8000/auth/session',
      token: token.substring(0, 10) + '...'
    })

    // FastAPIサーバーにセッション検証リクエストを送信
    const response = await fetch('http://localhost:8000/auth/session', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    console.log('FastAPIレスポンスステータス:', response.status)

    if (!response.ok) {
      const errorData = await response.text()
      console.error('FastAPIエラーレスポンス:', errorData)
      return NextResponse.json(
        { error: 'セッションが無効です' },
        { status: response.status }
      )
    }

    const data = await response.json()
    console.log('FastAPIレスポンス:', data)

    return NextResponse.json(data)
  } catch (error) {
    console.error('セッション検証エラー:', error)
    return NextResponse.json(
      { error: 'セッション検証に失敗しました' },
      { status: 500 }
    )
  }
} 