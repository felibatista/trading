import { Receipt } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatUsd } from '@/lib/format'
import type { Fill } from '@/lib/types'

export function HistoryTable({ fills }: { fills: Fill[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Historial de operaciones</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Símbolo</TableHead>
              <TableHead>Lado</TableHead>
              <TableHead className="text-right">Cantidad</TableHead>
              <TableHead className="text-right">Precio</TableHead>
              <TableHead className="text-right">Comisión</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fills.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={6}>
                  <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
                    <Receipt className="h-7 w-7 text-zinc-300" aria-hidden="true" />
                    <p className="text-sm font-medium text-zinc-600">Sin operaciones todavía</p>
                    <p className="text-xs text-zinc-400">Las órdenes ejecutadas se listarán aquí.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              fills.map((f, i) => (
                <TableRow key={`${f.ts}-${i}`}>
                  <TableCell className="font-mono tabular-nums text-zinc-500">{f.ts.slice(0, 16).replace('T', ' ')}</TableCell>
                  <TableCell className="font-mono font-semibold text-zinc-900">{f.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={f.side === 'BUY' ? 'success' : 'danger'}>
                      {f.side === 'BUY' ? 'COMPRA' : 'VENTA'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{f.quantity.toFixed(6)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{formatUsd(f.price)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-zinc-500">{formatUsd(f.fee)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
