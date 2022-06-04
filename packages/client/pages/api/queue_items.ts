import { handler } from '../../misc/requests';
import { urlparse } from '../../misc/utility';
import { ServiceType } from '../../services/constants';

export default handler().get(async (req, res) => {
  const server = global.app.service.get(ServiceType.Server);

  const {
    queue_type,
    limit,
    include_finished,
    include_queued,
    include_active,
  } = urlparse(req.url).query;

  return server
    .queue_items({
      queue_type: queue_type as number,
      limit: limit as number,
      include_finished: include_finished as boolean,
      include_queued: include_queued as boolean,
      include_active: include_active as boolean,
    })
    .then((r) => {
      res.status(200).json(r);
    });
});
