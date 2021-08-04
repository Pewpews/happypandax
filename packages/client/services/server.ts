import Client, {
  AnyJson,
  JsonMap,
  log,
  ServerErrorMsg,
  ServerMsg,
} from 'happypandax-client';

import { createCache } from '../misc/cache';
import { CommandState, ItemSort, ItemType } from '../misc/enums';
import {
  CommandID,
  CommandProgress,
  FieldPath,
  ProfileOptions,
  ServerItem,
  ServerMetaTags,
  ServerPage,
  ServerSortIndex,
} from '../misc/types';
import { Service } from './base';
import { ServiceType } from './constants';

export default class ServerService extends Service {
  cache: ReturnType<typeof createCache>;
  endpoint: { host: string; port: number };

  #client: Client;

  constructor(endpoint?: { host: string; port: number }) {
    super(ServiceType.Server);

    log.enabled = false;
    log.logger = {
      debug: global.app.log.d,
      info: global.app.log.i,
      warning: global.app.log.w,
      error: global.app.log.e,
    };

    // this avoiding recreating the hpx client during HMR
    this.#client =
      global.app?.hpx_client ?? new Client({ name: 'next-client' });
    global.app.hpx_client = this.#client;
    this.cache = global.app?.hpx_cache ?? createCache();
    global.app.hpx_cache = this.cache;

    this.endpoint = endpoint ?? { host: 'localhost', port: 7007 };
  }

  _throw_msg_error(msg: ServerMsg) {
    if (msg.error) {
      const msgerror: ServerErrorMsg = msg.error;
      const err = Error(`${msgerror.code}: ${msgerror.msg}`);
      err.data = msg;
      throw err;
    }
  }

  async _call(func: string, args: JsonMap) {
    global.app.log.d('calling', func, args);
    const data = await this.#client
      .send([
        {
          fname: func,
          ...args,
        },
      ])
      .then((d) => {
        global.app.log.d(func, 'received data');
        this._throw_msg_error(d);
        return d?.data?.[0];
      });

    return data;
  }

  get logged_in() {
    return this.#client._accepted;
  }

  status() {
    return {
      loggedIn: this.logged_in,
      connected: this.#client.is_connected(),
    };
  }

  async login(
    user?: string,
    password?: string,
    endpoint?: { host: string; port: number }
  ) {
    if (endpoint) {
      if (
        this.#client.is_connected() &&
        (endpoint.host !== this.endpoint.host ||
          endpoint.port !== this.endpoint.port)
      ) {
        global.app.log.i(
          'New HPX server endpoint specificed while old connection exists, closing old connection'
        );
        this.#client.close();
      }
      this.endpoint = endpoint;
    }

    if (!this.#client.is_connected()) {
      await this.#client.connect(this.endpoint);
    }

    const r = await this.#client
      .request_auth()
      .then((m) => this.#client.handshake({ user, password }));
    return r;
  }

  async item<R = undefined>(args: {
    item_type: ItemType;
    item_id: number;
    fields?: FieldPath[];
  }) {
    const data = await this._call('get_item', args);
    this._throw_msg_error(data);
    return data.data as R extends undefined ? JsonMap : R;
  }

  async items<R = undefined>(args: {
    item_type: ItemType;
    fields?: FieldPath[];
    offset?: number;
    limit?: number;
  }) {
    const data = await this._call('get_items', args);
    this._throw_msg_error(data);
    return data.data as {
      count: number;
      items: R extends undefined ? JsonMap[] : R[];
    };
  }

  async related_items<R = undefined>(args: {
    item_type: ItemType;
    item_id: number;
    related_type?: ItemType;
    fields?: FieldPath[];
    offset?: number;
    limit?: number;
  }) {
    const data = await this._call('get_related_items', args);
    this._throw_msg_error(data);
    return data.data as {
      count: number;
      items: R extends undefined ? JsonMap[] : R[];
    };
  }

  async pages(args: {
    gallery_id: number;
    number?: number;
    window_size?: number;
    fields?: FieldPath[];
    profile_options?: ProfileOptions;
  }) {
    const data = await this._call('get_pages', args);
    this._throw_msg_error(data);
    return data.data as {
      count: number;
      items: PartialExcept<ServerPage, 'id'>[];
    };
  }

  async profile(args: {
    item_type: ItemType;
    item_ids: number[];
    profile_options?: ProfileOptions;
  }) {
    const data = await this._call('get_profile', args);
    this._throw_msg_error(data);
    return data.data as { [key: string]: number };
  }

  async library<R = undefined>(args: {
    item_type: ItemType;
    fields?: FieldPath<R>[];
    page?: number;
    limit?: number;
    metatags?: Partial<Omit<ServerMetaTags, keyof ServerItem>>;
    filter_id?: number;
    sort_by?: ItemSort;
    sort_desc?: boolean;
    search_query?: string;
    search_options?: {};
  }) {
    const data = await this._call('library_view', args);
    this._throw_msg_error(data);
    return data.data as {
      count: number;
      items: R extends undefined ? JsonMap[] : R[];
    };
  }

  async sort_indexes(args: {
    item_type: ItemType;
    translate?: boolean;
    locale?: string;
  }) {
    const data = await this._call('get_sort_indexes', args);
    this._throw_msg_error(data);
    return data.data as ServerSortIndex[];
  }

  async start_command(args: { command_ids: number[] }) {
    const data = await this._call('start_command', args);
    this._throw_msg_error(data);
    return data.data as Record<CommandID, CommandState>;
  }

  async stop_command(args: { command_ids: number[] }) {
    const data = await this._call('stop_command', args);
    this._throw_msg_error(data);
    return data.data as Record<CommandID, CommandState>;
  }

  async command_state(args: { command_ids: number[] }) {
    const data = await this._call('get_command_state', args);
    this._throw_msg_error(data);
    return data.data as Record<CommandID, CommandState>;
  }

  async command_value(args: { command_ids: number[] }) {
    const data = await this._call('get_command_value', args);
    this._throw_msg_error(data);
    return data.data as Record<CommandID, AnyJson>;
  }

  async command_progress(args: { command_ids: number[] }) {
    const data = await this._call('get_command_progress', args);
    this._throw_msg_error(data);
    return data.data as Record<CommandID, CommandProgress>;
  }
}
