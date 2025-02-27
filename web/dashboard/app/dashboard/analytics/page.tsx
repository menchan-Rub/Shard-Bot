'use client'

import { useEffect, useCallback } from 'react'
import {
  Box,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Card,
  CardBody,
  Heading,
  useToast,
} from '@chakra-ui/react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

export default function AnalyticsPage() {
  const toast = useToast()

  const fetchData = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/stats`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (!response.ok) throw new Error('Failed to fetch analytics data')
      return await response.json()
    } catch (error) {
      toast({
        title: 'エラー',
        description: '統計データの取得に失敗しました',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    }
  }, [toast])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Bot Usage Statistics',
      },
    },
  }

  const data = {
    labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
    datasets: [
      {
        label: 'Commands Used',
        data: [65, 59, 80, 81, 56, 55, 40],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  }

  return (
    <Box>
      <Heading mb={6}>Overview</Heading>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Servers</StatLabel>
              <StatNumber>100</StatNumber>
              <StatHelpText>Active Discord Servers</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Users</StatLabel>
              <StatNumber>5,000</StatNumber>
              <StatHelpText>Across all servers</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Commands Used</StatLabel>
              <StatNumber>25,000</StatNumber>
              <StatHelpText>Last 30 days</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>
      <Card>
        <CardBody>
          <Line options={options} data={data} />
        </CardBody>
      </Card>
    </Box>
  )
} 