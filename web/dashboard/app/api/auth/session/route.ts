import { NextRequest, NextResponse } from 'next/server'

// APIエンドポイントの環境変数
const API_ENDPOINT = process.env.API_ENDPOINT || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    // リクエストヘッダーからトークンを取得
    const token = request.headers.get('authorization')?.replace('Bearer ', '')
    
    if (!token) {
      return NextResponse.json(
        { error: '認証に失敗しました' },
        { status: 401 }
      )
    }

    // 開発環境のみデバッグログを出力
    if (process.env.NODE_ENV === 'development') {
      console.log('セッション検証リクエスト送信', { url: `${API_ENDPOINT}/auth/session` })
    }

    // APIサーバーにセッション検証リクエストを送信
    const response = await fetch(`${API_ENDPOINT}/auth/session`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      // リクエストタイムアウトを設定
      signal: AbortSignal.timeout(5000)
    })

    // 開発環境のみデバッグログを出力
    if (process.env.NODE_ENV === 'development') {
      console.log('APIレスポンスステータス:', response.status)
    }

    if (!response.ok) {
      // エラーレスポンスの詳細をマスク
      return NextResponse.json(
        { error: '認証に失敗しました' },
        { status: response.status }
      )
    }

    const data = await response.json()
    
    // センシティブ情報をフィルタリング
    if (data.data?.user) {
      // 不要な情報を削除
      const { discord_access_token, ...safeUserData } = data.data.user
      data.data.user = safeUserData
    }

    return NextResponse.json(data)
  } catch (error) {
    // エラーの詳細は本番環境で隠す
    console.error('セッション検証エラー:', error)
    return NextResponse.json(
      { error: '認証処理に失敗しました' },
      { status: 500 }
    )
  }
} 