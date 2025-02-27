'use client'

import { useEffect, useCallback, useState } from 'react'
import {
  Box,
  VStack,
  FormControl,
  FormLabel,
  Switch,
  Select,
  Button,
  useToast,
  Heading,
} from '@chakra-ui/react'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    notifications: true,
    theme: 'light',
    language: 'ja',
  })
  const [isLoading, setIsLoading] = useState(true)
  const toast = useToast()

  const fetchSettings = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/settings`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (!response.ok) throw new Error('Failed to fetch settings')
      const data = await response.json()
      setSettings(data.data.settings)
    } catch (error) {
      toast({
        title: 'エラー',
        description: '設定の取得に失敗しました',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const handleSave = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })
      if (!response.ok) throw new Error('Failed to save settings')
      toast({
        title: '成功',
        description: '設定を保存しました',
        status: 'success',
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      toast({
        title: 'エラー',
        description: '設定の保存に失敗しました',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    }
  }

  if (isLoading) {
    return <Box>Loading...</Box>
  }

  return (
    <Box>
      <Heading mb={6}>設定</Heading>
      <VStack spacing={4} align="stretch">
        <FormControl display="flex" alignItems="center">
          <FormLabel mb="0">
            通知
          </FormLabel>
          <Switch
            isChecked={settings.notifications}
            onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}
          />
        </FormControl>

        <FormControl>
          <FormLabel>テーマ</FormLabel>
          <Select
            value={settings.theme}
            onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
          >
            <option value="light">ライト</option>
            <option value="dark">ダーク</option>
          </Select>
        </FormControl>

        <FormControl>
          <FormLabel>言語</FormLabel>
          <Select
            value={settings.language}
            onChange={(e) => setSettings({ ...settings, language: e.target.value })}
          >
            <option value="ja">日本語</option>
            <option value="en">English</option>
          </Select>
        </FormControl>

        <Button colorScheme="blue" onClick={handleSave}>
          保存
        </Button>
      </VStack>
    </Box>
  )
} 