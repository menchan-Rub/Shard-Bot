import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  console.log('API Route: リクエストを受信しました')
  
  try {
    // リクエストボディを取得
    const formData = await request.formData()
    const username = formData.get('username')
    const password = formData.get('password')
    
    console.log('フォームデータ:', { username, password: '***' })
    
    // FastAPIサーバーにリクエストを転送
    const apiUrl = 'http://localhost:8000/auth/login'
    console.log('FastAPIサーバーにリクエストを転送します:', apiUrl)
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      body: new URLSearchParams({
        username: username as string,
        password: password as string,
      }).toString(),
    })
    
    // レスポンスのヘッダーを確認
    console.log('FastAPIからのレスポンスステータス:', response.status)
    console.log('FastAPIからのレスポンスヘッダー:', Object.fromEntries(response.headers.entries()))
    
    // レスポンスを取得
    const responseData = await response.json()
    console.log('FastAPIからのレスポンス:', responseData)
    
    // クライアントにレスポンスを返す
    return NextResponse.json(responseData, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  } catch (error) {
    console.error('API Route エラー:', error)
    return NextResponse.json(
      { 
        status: 'error',
        detail: error instanceof Error ? error.message : 'Internal Server Error',
      },
      { status: 500 }
    )
  }
} 