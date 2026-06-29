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
        <CardTitle className="text-base font-semibold text-zinc-900">Historial de operaciones</CardTitle>
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
              <TableRow>
                <TableCell colSpan={6} className="text-center text-sm text-zinc-400">
                  Sin operaciones todavía.
                </TableCell>
              </TableRow>
            ) : (
              fills.map((f, i) => (
                <TableRow key={`${f.ts}-${i}`}>
                  <TableCell className="tabular-nums text-zinc-500">{f.ts.slice(0, 16).replace('T', ' ')}</TableCell>
                  <TableCell className="font-medium">{f.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={f.side === 'BUY' ? 'success' : 'danger'}>
                      {f.side === 'BUY' ? 'COMPRA' : 'VENTA'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{f.quantity.toFixed(6)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatUsd(f.price)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatUsd(f.fee)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
